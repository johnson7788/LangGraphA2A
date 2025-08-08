#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/6 10:18
# @File  : inject_command_tool.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : TODO，待完成

import dotenv
import os
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
    for token, metadata in agent.stream(inputs, stream_mode="messages"):
        print(token)
        print(metadata)
    print("\n【流式响应结束】")


