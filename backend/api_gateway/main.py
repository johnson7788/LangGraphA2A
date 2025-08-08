import time
import asyncio
import json
import os
import pika
import threading
from uuid import uuid4
from fastapi import FastAPI, Request, HTTPException
from fastapi.concurrency import run_in_threadpool
from sse_starlette.sse import EventSourceResponse
from pika.exceptions import AMQPConnectionError
import logging
from dotenv import load_dotenv
# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app initialization
app = FastAPI()

# RabbitMQ Configuration from environment variables
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USERNAME = os.getenv("RABBITMQ_USERNAME", "admin")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "welcome")
RABBITMQ_VIRTUAL_HOST = os.getenv("RABBITMQ_VIRTUAL_HOST", "/")
# 从哪个队列中读取数据,写入到问题，从答案读取
QUEUE_NAME_WRITER = os.getenv("QUEUE_NAME_WRITER", "question_queue")
QUEUE_NAME_READ = os.getenv("QUEUE_NAME_READ", "answer_queue")
logger.info(f"Connecting to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}, user: {RABBITMQ_USERNAME}")

# Thread-safe dictionary to store SSE queues for each session
sse_queues = {}

def get_rabbitmq_connection():
    """Creates and returns a new RabbitMQ connection."""
    credentials = pika.PlainCredentials(RABBITMQ_USERNAME, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VIRTUAL_HOST,
        credentials=credentials,
        heartbeat=600
    )
    try:
        return pika.BlockingConnection(parameters)
    except AMQPConnectionError as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        raise

def listen_to_answer_queue():
    """A long-running function to listen for messages on the answer queue."""
    while True:
        try:
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME_READ, durable=True)
            
            logger.info(f"Started listening to {QUEUE_NAME_READ}")

            for method_frame, properties, body in channel.consume(QUEUE_NAME_READ):
                try:
                    message = json.loads(body.decode('utf-8'))
                    session_id = message.get("sessionId")
                    if session_id in sse_queues:
                        sse_queues[session_id].put_nowait(message)
                    channel.basic_ack(method_frame.delivery_tag)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # It's safer to nack without requeue to avoid poison messages
                    channel.basic_nack(method_frame.delivery_tag, requeue=False)

        except (AMQPConnectionError, pika.exceptions.StreamLostError) as e:
            logger.error(f"RabbitMQ connection error in listener: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"An unexpected error occurred in the listener thread: {e}")
            # Avoid busy-looping on unexpected errors
            time.sleep(10)

def publish_to_question_queue(session_id: str, final_body: str):
    """Publishes a message to the question queue."""
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME_WRITER, durable=True)
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME_WRITER,
            body=final_body,
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            )
        )
        connection.close()
        logger.info(f"Sent message to {QUEUE_NAME_WRITER} for session {session_id}")
    except AMQPConnectionError as e:
        # Re-raise to be caught in the endpoint
        raise e

@app.on_event("startup")
async def startup_event():
    """Start the RabbitMQ listener thread on application startup."""
    listener_thread = threading.Thread(target=listen_to_answer_queue, daemon=True)
    listener_thread.start()

@app.post("/chat")
async def chat_endpoint(request: Request):
    """
    Receives a chat message, sends it to the question queue,
    and returns an SSE response to stream back answers.
    """
    try:
        data = await request.json()
        user_id = data.get("userId", "anonymous")
        messages = data.get("messages", [])
        
        if not messages:
            raise HTTPException(status_code=400, detail="Messages list cannot be empty.")

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    session_id = str(uuid4())
    
    # Prepare message for the message queue
    message_dict = {
        "sessionId": session_id,
        "userId": user_id,
        "functionId": 1,  # As per mq_backend logic
        "messages": messages
    }
    
    # Double JSON serialization
    json_string = json.dumps(message_dict, ensure_ascii=False)
    final_body = json.dumps(json_string)

    # Send message to RabbitMQ
    try:
        await run_in_threadpool(publish_to_question_queue, session_id, final_body)
    except AMQPConnectionError as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: Could not connect to message broker. {e}")

    async def event_generator():
        """Generator function for SSE."""
        # Create a queue for this specific request
        sse_queues[session_id] = asyncio.Queue()
        try:
            while True:
                message = await sse_queues[session_id].get()
                
                # If stop message is received, end the stream
                if message.get("message") == "[stop]":
                    yield {"event": "end", "data": json.dumps({"sessionId": session_id})}
                    break
                
                yield {"data": json.dumps(message)}

        except asyncio.CancelledError:
            logger.info(f"Client disconnected for session {session_id}.")
        finally:
            # Clean up the queue for this session
            if session_id in sse_queues:
                del sse_queues[session_id]
                logger.info(f"Cleaned up queue for session {session_id}")

    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9800)