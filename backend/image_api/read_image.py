#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/6/20 10:02
# @File  : tools.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 获取上一个research_agent所有使用到的原始文章中的图片

import re
import dotenv
import os
import time
from datetime import datetime
import random
import hashlib
from pathlib import Path
from openai import OpenAI, AsyncOpenAI # 导入 AsyncOpenAI
import asyncio # 导入 asyncio
from prompt import IMAGE_ANALYSIS_AGENT_PROMPT_CHINESE
from image_utils import async_cache_decorator
dotenv.load_dotenv()

VL_MODEL = "qwen-turbo-latest"
print(f"使用视觉模型进行图片理解: {VL_MODEL}")

def hash_md5_simple(n):
    s = str(n)
    return hashlib.md5(s.encode()).hexdigest()
@async_cache_decorator
async def recognize_image_scene(image_url: str, question: str) -> tuple[bool, str]: # 变为异步函数，返回类型改为元组
    """
    使用通义千问的视觉模型识别图片内容并回答问题。
    参数:
        image_url (str): 要识别的图片的URL。
        question (str): 用户提出的问题
    返回:
        tuple[bool, str]: (识别成功状态, 模型对图片的理解)。
        # 也可以这样输入
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
    """
    client = AsyncOpenAI( # <--- 使用 AsyncOpenAI
        api_key=os.getenv("ALI_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    vl_prompt = IMAGE_ANALYSIS_AGENT_PROMPT_CHINESE.format(question=question)
    try:
        response = await client.chat.completions.create( # <--- 使用 await
            model=VL_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": [{"type": "text", "text": vl_prompt}],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
        )
        image_description = response.choices[0].message.content
        print(f"图片{image_url}的识别结果: {image_description}")
        return True, image_description
    except Exception as e:
        print(f"识别图片 {image_url} 失败: {e}")
        return False, f"Error recognizing image: {e}"

if __name__ == '__main__':
    status, result = asyncio.run(recognize_image_scene(image_url="https://www.qcdy.com/uploads/allimg/150414/2-1504A1140.jpg", question="这个验血报告说明了什么?"))
    print(status)
    print(result)