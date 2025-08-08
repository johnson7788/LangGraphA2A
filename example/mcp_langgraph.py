#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/6 10:18
# @File  : invoke_langgraph.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 使用MCP, 首先启动mcp_search.py这个MCP工具，然后启动本程序

import dotenv
import os
import asyncio
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient


dotenv.load_dotenv()


# 定义一个简单的工具
@tool
def calculate_city_distance(city1: str, city2: str) -> str:
    """即使2个城市之间的距离"""
    return "200km"


async def build_agent():
    client = MultiServerMCPClient({
      "websearch": {
        "url": "http://localhost:9000/mcp",
        "transport": "streamable_http",
      }
    })
    tools = await client.get_tools()
    tools.append(calculate_city_distance)

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
        tools=tools
    )
    return agent

async def main():
    agent = await build_agent()
    inputs = {"messages": [HumanMessage(content="你好啊，介绍下什么是LangGraph")]}
    result_state = agent.invoke(inputs)
    new_messages = result_state["messages"]  # 包含工具调用、AI 回复等
    for m in new_messages:
        if isinstance(m, HumanMessage):
            print(f"{m.type}: {m.content}")
        elif isinstance(m, AIMessage):
            if m.tool_calls:
                # 工具调用
                print(f"{m.type}: {m.tool_calls}")
            else:
                print(f"{m.type}: {m.content}")
        elif isinstance(m, ToolMessage):
            print(f"{m.type}: {m.content}")

if __name__ == '__main__':
    asyncio.run(main())


