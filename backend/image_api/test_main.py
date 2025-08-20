
import os
import unittest
import time
import httpx
import asyncio
import json
from unittest.mock import patch, MagicMock, ANY
import pytest
from httpx import AsyncClient

class ImageAPITestCase(unittest.TestCase):
    """
    测试 FastAPI 接口
    """
    host = 'http://127.0.0.1'
    port = 9700
    env_host = os.environ.get('host')
    if env_host:
        host = env_host
    env_port = os.environ.get('port')
    if env_port:
        port = env_port
    base_url = f"{host}:{port}"

    def test_file_api(self):
        """
        测试文件的读取和识别
        """
        url = f"{self.base_url}/file"
        data = {}
        start_time = time.time()
        headers = {'content-type': 'application/json'}
        # 使用 httpx.stream 发起请求，并设置一个较大的超时时间或者不设置超时
        with httpx.stream("POST", url, json=data, headers=headers, timeout=None) as response:
            self.assertEqual(response.status_code, 200, "knowledge_base_chat_a2a 接口状态码应为 200")
            # 逐行读取流式响应内容
            for line in response.iter_lines():
                print(f"chat 响应片段: {line}")
        print(f"chat 测试花费时间: {time.time() - start_time}秒")
        print(f"调用的 server 是: {self.host}")
    def test_image_api(self):
        """
        测试图像的识别
        """
        url = f"{self.base_url}/image"
        data = {
        }
        start_time = time.time()
        headers = {'content-type': 'application/json'}
        # 使用 httpx.stream 发起请求，并设置一个较大的超时时间或者不设置超时
        with httpx.stream("POST", url, json=data, headers=headers, timeout=None) as response:
            self.assertEqual(response.status_code, 200, "knowledge_base_chat_a2a 接口状态码应为 200")
            # 逐行读取流式响应内容
            for line in response.iter_lines():
                print(f"chat 响应片段: {line}")
        print(f"chat 测试花费时间: {time.time() - start_time}秒")
        print(f"调用的 server 是: {self.host}")