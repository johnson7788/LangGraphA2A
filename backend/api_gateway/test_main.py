

import asyncio
import json
from unittest.mock import patch, MagicMock, ANY
import pytest
from httpx import AsyncClient
from api_gateway.main import app, sse_queues

# Use pytest-asyncio for async tests
@pytest.mark.asyncio
async def test_chat_endpoint_success():
    """
    Tests the /chat endpoint for a successful request and SSE streaming.
    Mocks RabbitMQ to isolate the test to the API gateway logic.
    """
    # Mock the RabbitMQ connection and channel
    mock_pika = MagicMock()

    # The main logic to test
    with patch('api_gateway.main.pika', mock_pika),
         patch('api_gateway.main.listen_to_answer_queue'): # Prevent listener thread from starting

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. Make the initial POST request to /chat
            chat_payload = {
                "userId": "test_user",
                "messages": [{"role": "user", "content": "Hello, world!"}]
            }
            response = await client.post("/chat", json=chat_payload, timeout=5)
            
            # Assert the POST request was successful
            assert response.status_code == 200
            assert response.headers['content-type'] == 'text/event-stream; charset=utf-8'

            # Extract the session_id from the mocked call to basic_publish
            # This is a bit complex due to double JSON encoding
            publish_args, publish_kwargs = mock_pika.BlockingConnection.return_value.channel.return_value.basic_publish.call_args
            body = json.loads(json.loads(publish_kwargs["body"]))
            session_id = body["sessionId"]
            
            assert session_id is not None
            assert session_id in sse_queues

            # 2. Simulate receiving messages from RabbitMQ for the SSE response
            async def stream_mock_data():
                # Allow the event_generator in the endpoint to set up the queue
                await asyncio.sleep(0.1)
                
                # Mock data that the listener thread would normally put in the queue
                mock_response_part1 = {"sessionId": session_id, "message": "This is a test."}
                mock_response_part2 = {"sessionId": session_id, "message": "[stop]"}

                await sse_queues[session_id].put(mock_response_part1)
                await asyncio.sleep(0.1)
                await sse_queues[session_id].put(mock_response_part2)

            # Run the streaming simulation concurrently with reading the response
            streaming_task = asyncio.create_task(stream_mock_data())

            # 3. Collect the SSE events from the response
            sse_events = []
            sse_raw = ""
            async for line in response.aiter_lines():
                sse_raw += line + "\n"
                if line.startswith('data:'):
                    data_json = line[len('data:'):].strip()
                    sse_events.append(json.loads(data_json))
                elif line.startswith('event: end'):
                    # The stop message should trigger the 'end' event
                    sse_events.append({"event": "end"})

            await streaming_task

            # 4. Assert the results
            # Check that the message was sent to RabbitMQ correctly
            mock_pika.BlockingConnection.return_value.channel.return_value.basic_publish.assert_called_once_with(
                exchange='',
                routing_key=ANY, # routing_key can be from env
                body=ANY, # body is checked above for session_id
                properties=ANY
            )

            # Check the received SSE events
            assert len(sse_events) == 2
            assert sse_events[0]["message"] == "This is a test."
            assert sse_events[1]["event"] == "end"
            
            # Check that the queue was cleaned up
            assert session_id not in sse_queues

@pytest.mark.asyncio
async def test_chat_endpoint_invalid_payload():
    """
    Tests the /chat endpoint with an invalid JSON payload.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/chat", content="not a json")
        assert response.status_code == 400
        assert "Invalid JSON payload" in response.text

@pytest.mark.asyncio
async def test_chat_endpoint_empty_messages():
    """
    Tests the /chat endpoint with an empty messages list.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        chat_payload = {"userId": "test_user", "messages": []}
        response = await client.post("/chat", json=chat_payload)
        assert response.status_code == 400
        assert "Messages list cannot be empty" in response.text

