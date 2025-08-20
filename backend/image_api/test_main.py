import os
import unittest
import time
import httpx

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
        data = {
            "file_path": "https://rahacollege.co.in/learning/38.pdf",
            "question": "请总结一下这个文档的内容"
        }
        start_time = time.time()
        headers = {'content-type': 'application/json'}
        # 使用 httpx.post 发起请求
        response = httpx.post(url, json=data, headers=headers, timeout=30.0)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        print(f"API 响应: {result}")
        self.assertTrue(result['success'])
        self.assertIn("result", result)
        print(f"chat 测试花费时间: {time.time() - start_time}秒")
        print(f"调用的 server 是: {self.host}")

    def test_image_api(self):
        """
        测试图像的识别
        """
        url = f"{self.base_url}/image"
        data = {
            "image_url": "https://www.qcdy.com/uploads/allimg/150414/2-1504A1140.jpg",
            "question": "这张图片里有什么？"
        }
        start_time = time.time()
        headers = {'content-type': 'application/json'}
        # 使用 httpx.post 发起请求
        response = httpx.post(url, json=data, headers=headers, timeout=30.0)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        print(f"API 响应: {result}")
        self.assertTrue(result['success'])
        self.assertIn("result", result)
        print(f"chat 测试花费时间: {time.time() - start_time}秒")
        print(f"调用的 server 是: {self.host}")