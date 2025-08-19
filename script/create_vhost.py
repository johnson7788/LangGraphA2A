#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/19 13:35
# @File  : create_vhost.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 创建Rabbit MQ的 vhost
# 输出结果
# 虚拟主机 'hello' 创建成功
# 结果：虚拟主机创建成功


import requests
from requests.auth import HTTPBasicAuth


def create_vhost(vhost_name, host='localhost', port=15672, username='admin', password='welcome'):
    try:
        # 构建 API 端点
        url = f'http://{host}:{port}/api/vhosts/{vhost_name}'

        # 发送 POST 请求创建虚拟主机
        response = requests.put(
            url,
            auth=HTTPBasicAuth(username, password),
            headers={'Content-Type': 'application/json'}
        )

        # 检查响应
        if response.status_code == 201 or response.status_code == 204:
            print(f"虚拟主机 '{vhost_name}' 创建成功")
            return True, "虚拟主机创建成功"
        elif response.status_code == 400:
            print(f"错误：虚拟主机 '{vhost_name}' 可能已存在")
            return False, "虚拟主机可能已存在"
        else:
            print(f"错误：创建虚拟主机失败，状态码 {response.status_code}，响应：{response.text}")
            return False, f"创建失败：{response.text}"
    except requests.exceptions.RequestException as e:
        print(f"连接错误：{e}")
        return False, f"连接错误：{e}"


if __name__ == '__main__':
    vhost_name = 'hello'
    success, message = create_vhost(vhost_name)
    print(f"结果：{message}")

