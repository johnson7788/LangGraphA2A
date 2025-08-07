#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/6 10:18
# @File  : inject_command_tool.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 流式的返回数据

import dotenv
import json
import os
from collections import defaultdict
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

dotenv.load_dotenv()


# 定义一个简单的工具
@tool
def web_search(query: str) -> str:
    """网络搜索"""
    return f"LangGraph核心技术概念，LangGraph和LangChain同宗同源，底层架构完全相同、接口完全相通。从开发者角度来说，LangGraph也是使用LangChain底层API来接入各类大模型、LangGraph也完全兼容LangChain内置的一系列工具。换而言之，LangGraph的核心功能都是依托LangChain来完成。但是和LangChain的链式工作流哲学完全不同的是，LangGraph的基础哲学是构建图结构的工作流，并引入“状态”这一核心概念来描绘任务执行情况，从而拓展了LangChain LCEL链式语法的功能灵活程度。"


# 初始化模型
model = ChatOpenAI(
    model="gpt-4.1",
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    openai_api_base=os.getenv('OPENAI_API_BASE'),
    temperature=0
)

# 构建 Agent
agent = create_react_agent(
    model=model,
    prompt="使用web_search搜索后回答用户的问题",
    tools=[web_search]
)

if __name__ == '__main__':
    inputs = {"messages": [HumanMessage(content="你好啊，介绍下什么是LangGraph")]}
    print("【流式响应开始】")

    buffer = ""  # 收集普通语言内容
    tool_chunks = []  # 收集 tool_call_chunk 分片

    for token, metadata in agent.stream(inputs, stream_mode="messages"):
        content = token.content or ""
        tool_call_chunks = token.additional_kwargs.get("tool_calls", [])

        if tool_call_chunks:
            # 收集工具调用分片
            tool_chunks.extend(tool_call_chunks)
            continue

        elif content:
            # 输出普通内容（语言响应）
            print(content, flush=True)

        elif "finish_reason" in token.response_metadata and token.response_metadata["finish_reason"] == "tool_calls":
            # 工具调用流结束，开始合并
            merged_calls = defaultdict(lambda: {
                "args": "",
                "name": None,
                "type": None,
                "id": None
            })

            for chunk in tool_chunks:
                index = chunk.get("index", 0)
                merged = merged_calls[index]
                merged["args"] += chunk.get("function", {}).get("arguments","")
                merged["name"] = chunk.get("function", {}).get("name","") or merged["name"]
                merged["type"] = chunk.get("type") or merged["type"]
                merged["id"] = chunk.get("id") or merged["id"]

            # 构建最终 tool_calls 列表
            final_tool_calls = []
            for idx in sorted(merged_calls.keys()):
                info = merged_calls[idx]
                try:
                    arguments_obj = json.loads(info["args"])
                except json.JSONDecodeError:
                    arguments_obj = info["args"]  # 保留原始字符串以便调试

                call = {
                    "index": idx,
                    "id": info["id"],
                    "type": info["type"],
                    "function": {
                        "name": info["name"],
                        "arguments": arguments_obj
                    }
                }
                final_tool_calls.append(call)

            print(f"\ntool_calls={final_tool_calls}\n")
            tool_chunks.clear()

    print("\n【流式响应结束】")


