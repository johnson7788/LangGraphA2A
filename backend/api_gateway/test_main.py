
import os
import unittest
import time
import httpx
import asyncio
import json
from unittest.mock import patch, MagicMock, ANY
import pytest
from httpx import AsyncClient

class KnowledgeBaseTestCase(unittest.TestCase):
    """
    测试 FastAPI 接口
    """
    host = 'http://127.0.0.1'
    port = 9800
    env_host = os.environ.get('host')
    if env_host:
        host = env_host
    env_port = os.environ.get('port')
    if env_port:
        port = env_port
    base_url = f"{host}:{port}"

    def test_knowledge_base_chat(self):
        """
        测试Agent chat（流式响应)
        """
        url = f"{self.base_url}/chat"
        data = {
            "userId": "123456",
            "messages": [{"role": "user", "content": "Hello"}]
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
    def test_knowledge_base_chat_history(self):
        """
        测试Agent chat（流式响应)
        """
        url = f"{self.base_url}/chat"
        data = {
            "userId": "123456",
            "messages": [{'role': 'user', 'content': "我叫Johnson Guo"}, {'role': 'ai', 'content': "很高兴认识你"}, {"role": "user", "content": "你知道我叫什么吗?"}]
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
    def test_knowledge_base_chat_tools(self):
        """
        测试Agent chat（流式响应)
        """
        url = f"{self.base_url}/chat"
        data = {
            "userId": "123456",
            "messages": [{"role": "user", "content": "帕金森的治疗方案有哪些?"}],
            "attachment": {"tools": ["search_document_db"]}
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
    def test_knowledge_get_data_source(self):
        """
        返回结果
         [{"id":"search_document_db","name":"search_document_db","description":"搜索文献库","type":"literature"},{"id":"search_personal_db","name":"search_personal_db","description":"搜索个人数据库","type":"database"},{"id":"search_guideline_db","name":"search_guideline_db","description":"搜索指南数据库","type":"knowledge_base"}]
        """
        url = f"{self.base_url}/get_data_source"
        start_time = time.time()
        headers = {'content-type': 'application/json'}
        with httpx.Client() as client:
            response = client.get(url, headers=headers)
            print(response.json())
            self.assertEqual(response.status_code, 200)
        print(f"get_data_source test took: {time.time() - start_time}s")
        print(f"调用的 server 是: {self.host}")
    def test_knowledge_validate_mcp(self):
        """
        Post
        返回结果
        {'status': 'ok', 'message': 'Successfully connected to MCP server and listed tools.', 'tools': {'_meta': None, 'nextCursor': None, 'tools': [{'name': 'search_document_db', 'title': None, 'description': '\n    模拟搜索文献库：包括标题、snippet、content、来源、时间等。\n\n    Args:\n        query (str): 搜索查询关键词\n        max_results (int, optional): 最大返回结果数量，默认为3\n\n    Returns:\n        list: 包含文献信息的字典列表，每个字典包含title, snippet, content, source, timestamp字段\n    ', 'inputSchema': {'properties': {'query': {'title': 'Query', 'type': 'string'}, 'max_results': {'default': 3, 'title': 'Max Results', 'type': 'integer'}}, 'required': ['query'], 'title': 'search_document_dbArguments', 'type': 'object'}, 'outputSchema': None, 'annotations': None, '_meta': None}]}}
        """
        url = f"{self.base_url}/validate_mcp"
        data = {"url": "http://localhost:9000/sse"}
        start_time = time.time()
        headers = {'content-type': 'application/json'}
        with httpx.Client() as client:
            response = client.post(url, json=data, headers=headers)
            self.assertEqual(response.status_code, 200)
            response_data = response.json()
            print(response_data)
            self.assertEqual(response_data["status"], "ok")
            self.assertIn("tools", response_data)
            self.assertIsInstance(response_data["tools"]["tools"], list)
        print(f"validate_mcp test took: {time.time() - start_time}s")
        print(f"调用的 server 是: {self.host}")