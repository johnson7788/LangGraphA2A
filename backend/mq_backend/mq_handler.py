#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime
import pika

RABBITMQ_HOST = os.environ["RABBITMQ_HOST"]
RABBITMQ_PORT = os.environ["RABBITMQ_PORT"]
RABBITMQ_USERNAME = os.environ["RABBITMQ_USERNAME"]
RABBITMQ_PASSWORD = os.environ["RABBITMQ_PASSWORD"]
RABBITMQ_VIRTUAL_HOST = os.environ["RABBITMQ_VIRTUAL_HOST"]
QUEUE_NAME_ANSWER = os.environ["QUEUE_NAME_ANSWER"]
QUEUE_NAME_QUESTION = os.environ["QUEUE_NAME_QUESTION"]

class MQHandler:
    def __init__(self, host, port, username, password, virtual_host, queue_name):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.virtual_host = virtual_host
        self.queue_name = queue_name
        self.credentials = pika.PlainCredentials(self.username, self.password)
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.virtual_host,
                credentials=self.credentials
            )
        )
        self.channel = self.connection.channel()
        # 声明一个持久化队列
        self.channel.queue_declare(queue=self.queue_name, durable=True)

    def send_message(self, message_dict):
        try:
            self.channel.basic_publish(exchange='', routing_key=self.queue_name, body=json.dumps(message_dict))
            print(" [🚚] 发送消息到mq：", message_dict)

            message_type = message_dict.get('type')
            message_content = message_dict.get('message')

            if message_type in {1, 2} or (message_type == 4 and message_content == '[stop]'):
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅ - {timestamp}")
        except KeyError as ke:
            print(f"消息结构中缺少关键字段：{ke}")
        except Exception as e:
            print(f"发送消息时发生错误：{e}")

    def close_connection(self):
        self.connection.close()

    def consume_messages(self, callback, auto_ack=True):
        # 告诉 RabbitMQ 使用回调函数来接收消息，并且一次只分发一条消息
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=callback, auto_ack=auto_ack)
        print(f' [🐷] Waiting for messages. To exit press CTRL+C - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        # 开始接收消息
        self.channel.start_consuming()


def send_to_mq2(message, handler):
    handler.send_message(message)


def send_to_mq(message):
    handler = MQHandler(RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD, RABBITMQ_VIRTUAL_HOST,
                        QUEUE_NAME_ANSWER)
    handler.send_message(message)
    handler.close_connection()


def start_consumer(callback, auto_ack=True):
    handler = MQHandler(RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD, RABBITMQ_VIRTUAL_HOST,
                        QUEUE_NAME_QUESTION)
    handler.consume_messages(callback, auto_ack=auto_ack)
