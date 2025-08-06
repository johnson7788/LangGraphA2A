#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/6 10:59
# @File  : models.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :
import os
import httpx
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

http_client = httpx.Client(proxies={
    os.getenv("HTTP_PROXY"),
    os.getenv("HTTPS_PROXY"),
})
def create_model():
    MODEL_PROVIDER = os.getenv('MODEL_PROVIDER')
    LLM_MODEL = os.getenv('LLM_MODEL')
    print(f"使用的模型为：{MODEL_PROVIDER} 的 {LLM_MODEL}")
    if MODEL_PROVIDER == 'google':
        model = ChatGoogleGenerativeAI(model='gemini-2.0-flash')
    elif MODEL_PROVIDER == 'openai':
        model = ChatOpenAI(
            model=os.getenv('LLM_MODEL'),
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            temperature=0,
            http_client=http_client
        )
    elif MODEL_PROVIDER == "deepseek":
        model = ChatOpenAI(
            model=os.getenv('LLM_MODEL'),
            api_key=os.getenv('DEEPSEEK_API_KEY'),
            base_url="https://api.deepseek.com/v1",
            temperature=0,
        )
    else:
        raise Exception("无效的模型Provider，请修改环境变量.env文件")
    return model