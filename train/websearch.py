#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/29 21:42
# @File  : websearch.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :
import os

import dotenv
from pydantic import BaseModel, Field
from zai import ZhipuAiClient
dotenv.load_dotenv()
class WebSearchResult(BaseModel):
    url: str
    title: str
    snippet: str

WebSearchClient = ZhipuAiClient(api_key=os.environ["ZHIPU_API_KEY"])
response = WebSearchClient.web_search.web_search(
        search_engine="search_std",
        search_query="搜索2025年4月的财经新闻",
        count=15,  # 返回结果的条数，范围1-50，默认10
        search_recency_filter="noLimit",  # 搜索指定日期范围内的内容
        content_size="high"  # 控制网页摘要的字数，默认medium
    )
if not response.search_result:
    print()

result = [
        WebSearchResult(
            url=sr.link,
            title=sr.title,
            snippet=sr.content
        )
        for sr in response.search_result
]

print(result)