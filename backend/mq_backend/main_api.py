#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 用于和rabbitMQ进行交互
import os
import random
import string
import time
import json
import asyncio
import traceback
import dotenv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from mq_handler import start_consumer, MQHandler
from A2Aclient import A2AClientWrapper
dotenv.load_dotenv()


# 创建一个线程池，定义线程池的大小10
executor = ThreadPoolExecutor(max_workers=20)

RABBITMQ_HOST = os.environ["RABBITMQ_HOST"]
RABBITMQ_PORT = os.environ["RABBITMQ_PORT"]
RABBITMQ_USERNAME = os.environ["RABBITMQ_USERNAME"]
RABBITMQ_PASSWORD = os.environ["RABBITMQ_PASSWORD"]
RABBITMQ_VIRTUAL_HOST = os.environ["RABBITMQ_VIRTUAL_HOST"]
QUEUE_NAME_ANSWER = os.environ["QUEUE_NAME_ANSWER"]
QUEUE_NAME_QUESTION = os.environ["QUEUE_NAME_QUESTION"]
AGENT_URL = os.environ["AGENT_URL"]

def handle_gpt_stream_response(session_id, user_id, function_id, stream_response):
    """
    处理GPT流式响应
    """
    mq_handler = MQHandler(RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD, RABBITMQ_VIRTUAL_HOST,
                           QUEUE_NAME_ANSWER)
    # 如果发生错误，先处理错误：stream_response是字符串就是错误，应该默认是生成器
    def send_error_message(error_msg):
        """发送错误信息到消息队列"""
        mq_handler.send_message({
            "sessionId": session_id,
            "userId": user_id,
            "functionId": function_id,
            "message": f'发生错误：{error_msg}',
            "reasoningMessage": "",
            "type": 4,
        })
        time.sleep(0.01)
        mq_handler.send_message({
            "sessionId": session_id,
            "userId": user_id,
            "functionId": function_id,
            "message": '[stop]',
            "reasoningMessage": "",
            "type": 4,
        })

    if isinstance(stream_response, str):
        send_error_message(stream_response)
        mq_handler.close_connection()
        return
    async def consume():
        try:
            async for chunk in stream_response:
                try:
                    data_type = chunk.get("type")
                    if data_type == "final":
                        answer_queue_message = {
                            "sessionId": session_id,
                            "userId": user_id,
                            "functionId": function_id,
                            "message": '[stop]',
                            "reasoningMessage": "",
                            "type": 4,
                        }
                    elif data_type == "reasoning":
                        answer_queue_message = {
                            "sessionId": session_id,
                            "userId": user_id,
                            "functionId": function_id,
                            "message": '',
                            "reasoningMessage": chunk.get("reasoning", ""),
                            "type": 4,
                        }
                    elif data_type == "text":
                        answer_queue_message = {
                            "sessionId": session_id,
                            "userId": user_id,
                            "functionId": function_id,
                            "message": chunk.get("text", ""),
                            "reasoningMessage": '',
                            "type": 4,
                        }
                    elif data_type == "data":
                        chunk_data = chunk.get("data", {})
                        tools_data = chunk_data.get("data", [])
                        # 发送给前端的数据，list格式，里面是字典
                        front_data = [tool["front_data"] for tool in tools_data]
                        #工具是调用还是结束了，只需要工具结束了的数据
                        tool_type = chunk_data.get("type")
                        answer_queue_message = {
                            "sessionId": session_id,
                            "userId": user_id,
                            "functionId": function_id,
                            "message": json.dumps(front_data, ensure_ascii=False),
                            "reasoningMessage": "",
                            "type": 5,
                        }
                        print(f"[Info] 发送状态数据完成（type 5)：{answer_queue_message}")
                        # 发送引用数据和参考，即匹配的结果
                        if tool_type == "tool_result":
                            tool_retrieve_data = [one.get("data",{}) for one in tools_data]
                            answer_reference = {
                                "sessionId": session_id,
                                "userId": user_id,
                                "functionId": function_id,
                                "message": json.dumps(tool_retrieve_data, ensure_ascii=False),
                                "reasoningMessage": "",
                                "type": 6,
                            }
                            mq_handler.send_message(answer_reference)
                            print(f"[Info] 发送引用和参考数据完成(type 6)：{answer_reference}")
                    elif data_type == "artifact":
                        print(f"[Info] 收到artifact数据，如果我们设置的Stream，那么这条数据需要忽略：{chunk}")
                    else:
                        print(f"[警告] 未知的chunk类型：{data_type}，已跳过")
                        continue

                    mq_handler.send_message(answer_queue_message)
                    if function_id not in [5000, 9001]:
                        time.sleep(0.01)
                except Exception as chunk_error:
                    print("[错误] 处理 chunk 时发生异常：", chunk_error)
                    traceback.print_exc()
                    send_error_message(f"处理数据块出错：{chunk_error}")
        except Exception as stream_error:
            print("[错误] 流消费失败：", stream_error)
            traceback.print_exc()
            send_error_message(f"处理流出错：{stream_error}")
        finally:
            mq_handler.close_connection()

    asyncio.run(consume())


def handle_rabbit_queue_message(rabbit_message):
    """
    处理从RabbitMQ 队列接收到的消息
    """
    # 解析mq消息
    print(f"处理消息handle_rabbit_queue_message: {rabbit_message}")
    session_id = rabbit_message['sessionId']
    user_id = rabbit_message['userId']
    function_id = rabbit_message['functionId']
    messages = rabbit_message['messages']
    user_question_dict = messages.pop()
    user_question = user_question_dict["content"]
    # attachment = rabbit_message['attachment']
    # link_id = rabbit_message.get('linkId', None)

    if function_id == 1:
        # Agent RAG的问答
        wrapper = A2AClientWrapper(session_id=session_id, agent_url=AGENT_URL)
        stream_response = wrapper.generate(user_question=user_question, history=messages)
        handle_gpt_stream_response(session_id, user_id, function_id, stream_response)
    else:
        print('不在进行处理这条消息，function_id NOT  : ' + str(function_id))
        return



def callback(ch, method, properties, body):
    """
    mq接收到消息后的回调函数，多线程处理
    """
    try:
        # 接收到mq的消息：转换成dict
        print(f"😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁😁 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        rabbit_message = json.loads(json.loads(body.decode('utf-8')))
        print(f" [🚚] 从mq接受到消息：{rabbit_message}")
        # 提交任务到线程池
        executor.submit(handle_rabbit_queue_message, rabbit_message)
        # 手动发送消息确认
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"处理消息时出错: {e}")
        # 出错时拒绝消息并重新入队
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


if __name__ == '__main__':
    start_consumer(callback, auto_ack=False)
