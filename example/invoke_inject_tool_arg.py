#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/18 09:31
# @File  : invoke_inject.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : InjectedToolArg有些问题，使用state代替

import dotenv
import os
from typing import Annotated, NotRequired
from langchain_core.tools import InjectedToolArg
from typing_extensions import Annotated
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.prebuilt import InjectedState
from langchain_core.tools import tool
import langchain_core


dotenv.load_dotenv()

class CustomState(AgentState):
    user_name: NotRequired[str]
# 定义一个工具：除了 query (LLM决定) 还要 user_id (系统注入)
@tool
def web_search(query: str, state: Annotated[dict, InjectedState]) -> str:
    """
    网络搜索工具。

    Args:
        query: 搜索的内容（LLM 生成）。
        tool_runtime: 系统注入的用户 ID。
    """
    user_name = state.get("user_name", "unknown")
    print(f"Web Search, 参数query: {query}, user_name: {user_name}")
    return f"搜索结果: LangGraph 核心技术概念 ..."

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
    tools=[web_search],
    state_schema=CustomState,
)

if __name__ == '__main__':
    # 给LLM输入 & 给系统注入参数
    # 用户名这个参数可选可不选, 这个是传入
    inputs = {
        "messages": [HumanMessage(content="你好啊，介绍下什么是LangGraph")],
        "user_name": "Bobby",
    }
    #
    # 用户名这个参数可选可不选，不传入
    # inputs = {
    #     "messages": [HumanMessage(content="你好啊，介绍下什么是LangGraph")]
    # }
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
