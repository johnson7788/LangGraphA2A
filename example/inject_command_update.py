#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/6 10:18
# @File  : inject_command_tool.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 工具的state的写如多个结果， 使用operator.add进行追加工具的输出结果
import dotenv
import os
import json
from typing import Annotated, NotRequired
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from typing import Annotated
from langgraph.types import Command
import operator
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool, InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
dotenv.load_dotenv()

memory = MemorySaver()

class CustomState(AgentState):
    search_dbs: Annotated[list[str], operator.add]

@tool
def search_web_db(
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Update user-name in short-term memory."""
    return Command(update={
        "search_dbs": ["search_web_db"],
        "messages": [
            ToolMessage(f"特斯拉的创始人是马斯克", tool_call_id=tool_call_id)
        ]
    })

@tool
def search_personal_db(
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Update user-name in short-term memory."""
    return Command(update={
        "search_dbs": ["search_personal_db"],
        "messages": [
            ToolMessage(f"公司内部消息，特斯拉新款飞行汽车X9内测中。", tool_call_id=tool_call_id)
        ]
    })


model = ChatOpenAI(model="gpt-4.1",
                openai_api_key=os.getenv('OPENAI_API_KEY'),
                openai_api_base=os.getenv('OPENAI_API_BASE'),
                temperature=0)
# Example agent setup
agent = create_react_agent(
    model=model,
    tools=[search_web_db, search_personal_db],
    state_schema=CustomState,
    checkpointer=memory,
)

if __name__ == '__main__':
    # Invocation: reads the name from state (initially empty)
    # agent.invoke({"messages": "what's my name?"})  # 简写方法
    config = {'configurable': {'thread_id': "testid_12345"}}
    response = agent.invoke({"messages": [{"role": "user", "content": "搜索个人和网络内容，总结特斯拉的相关新闻"}]}, config=config)
    print(response)

