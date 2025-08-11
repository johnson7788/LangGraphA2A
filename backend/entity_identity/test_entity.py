#!/usr/bin/env /Users/admin/virtulenv/py38/bin/python
# -*- coding: utf-8 -*-
import unittest
import warnings
import requests
import time, os
import json
import base64
import random
import string
import hashlib
import pickle
import sys
import httpx


class EntityIdentifyTestCase(unittest.TestCase):
    host = '127.0.0.1'
    env_host = os.environ.get('host')
    if env_host:
        host = env_host
    env_port = os.environ.get('port')
    if env_port:
        port = env_port
    port = 6200
    def test_ping(self):
        """测试服务连通性"""
        url = f"http://{self.host}:{self.port}/ping"
        res = requests.get(url)
        print(json.dumps(res.json(), ensure_ascii=False, indent=4))
        self.assertEqual(res.text, '"Pong"', "服务未正常响应")
    def test_entity_indentify_extract(self):
        """测试entity_indentify_extract识别接口"""
        url = f"http://{self.host}:{self.port}/api/entity_indentify"
        start_time = time.time()
        headers = {'content-type': 'application/json'}
        data = {"content": "近年来，糖尿病患者数量逐年上升，常用的治疗药物包括二甲双胍、胰岛素等。部分患者还伴有高血压，需要服用氯沙坦或硝苯地平进行控制。"}
        r = requests.post(url, data=json.dumps(data), headers=headers)
        assert r.status_code == 200, f"返回的status code不是200，请检查"
        # 检查转换结果
        res = r.json()
        print(json.dumps(res, indent=4, ensure_ascii=False))
        msg = res.get("msg")
        assert msg == "success", f"接口返回的msg不是成功，请检查"
        print(f"花费时间: {time.time() - start_time}秒")
    def test_entity_indentify_extract_match_db(self):
        """测试entity_indentify_extract识别接口"""
        url = f"http://{self.host}:{self.port}/api/entity_indentify"
        start_time = time.time()
        headers = {'content-type': 'application/json'}
        data = {"match_db": True,"content": "近年来，糖尿病患者数量逐年上升，常用的治疗药物包括盐酸二甲双胍片、胰岛素注射液等。部分患者还伴有高血压，需要服用氯沙坦或硝苯地平进行控制。"}
        r = requests.post(url, data=json.dumps(data), headers=headers)
        assert r.status_code == 200, f"返回的status code不是200，请检查"
        # 检查转换结果
        res = r.json()
        print(json.dumps(res, indent=4, ensure_ascii=False))
        msg = res.get("msg")
        assert msg == "success", f"接口返回的msg不是成功，请检查"
        print(f"花费时间: {time.time() - start_time}秒")
    def test_match_drug_disease(self):
        """测试match_drug_disease识别接口"""
        url = f"http://{self.host}:{self.port}/api/match_drug_disease"
        start_time = time.time()
        headers = {'content-type': 'application/json'}
        data = {"disease_names": ["高血压","糖尿病"], "drug_names": ["盐酸二甲双胍片","胰岛素注射液","氯沙坦","硝苯地平"]}
        r = requests.post(url, data=json.dumps(data), headers=headers)
        assert r.status_code == 200, f"返回的status code不是200，请检查"
        # 检查转换结果
        res = r.json()
        print(json.dumps(res, indent=4, ensure_ascii=False))
        msg = res.get("msg")
        assert msg == "success", f"接口返回的msg不是成功，请检查"
        print(f"花费时间: {time.time() - start_time}秒")

if __name__ == '__main__':
    ##确保Flask server已经启动
    unittest.main()
