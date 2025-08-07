#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/6/5 11:50
# @File  : test_api.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 测试Rabbit MQ的写入

import asyncio
import base64
import os
import urllib
import sys
from uuid import uuid4
import json
import unittest
import random
import string
import pika
import dotenv
dotenv.load_dotenv()

RABBITMQ_HOST = os.environ["RABBITMQ_HOST"]
RABBITMQ_PORT = os.environ["RABBITMQ_PORT"]
RABBITMQ_USERNAME = os.environ["RABBITMQ_USERNAME"]
RABBITMQ_PASSWORD = os.environ["RABBITMQ_PASSWORD"]
RABBITMQ_VIRTUAL_HOST = os.environ["RABBITMQ_VIRTUAL_HOST"]
QUEUE_NAME_ANSWER = os.environ["QUEUE_NAME_ANSWER"]
QUEUE_NAME_QUESTION = os.environ["QUEUE_NAME_QUESTION"]


class MQClientTestCase(unittest.IsolatedAsyncioTestCase):
    """
    测试 MQ客户端的功能
    """
    def test_publish_message(self):
        # 自定义一些数据格式
        data = {"sessionId": uuid4().hex, "userId": "johnson", "functionId":1, "messages":  [{"role": "user", "content": "帕金森的治疗方案有哪些?"}]}
        json_data = json.dumps(data, ensure_ascii=False)
        nest_json_data = json.dumps(json_data)
        # 建立与RabbitMQ服务器的连接
        credentials = pika.PlainCredentials(RABBITMQ_USERNAME, RABBITMQ_PASSWORD)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                virtual_host=RABBITMQ_VIRTUAL_HOST,
                credentials=credentials
            )
        )
        channel = connection.channel()
        # 声明一个队列
        channel.queue_declare(queue=QUEUE_NAME_QUESTION, durable=True)

        # 发送消息
        channel.basic_publish(exchange='',
                              routing_key=QUEUE_NAME_QUESTION,
                              body=nest_json_data)
        print(f"发送一条消息到Rabbit MQ完成: '{data}'")
        # 关闭连接
        connection.close()

async def main():
    test_case = MQClientTestCase()
    # 发送一条信息
    test_case.test_publish_message()

if __name__ == "__main__":
    asyncio.run(main())