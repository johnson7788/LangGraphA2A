#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/6 10:18
# @File  : inject_command_tool.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 工具的state的读取和写入
import dotenv
import os
import json
from typing import Annotated, NotRequired
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from typing import Annotated
from langgraph.types import Command
from langchain_core.tools import tool, InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
dotenv.load_dotenv()

memory = MemorySaver()

class CustomState(AgentState):
    # The user_name field in short-term state
    user_name: NotRequired[str]

@tool
def get_user_name(
    state: Annotated[CustomState, InjectedState]
) -> str:
    """Retrieve the current user-name from state."""
    # Return stored name or a default if not set
    return state.get("user_name", "Unknown user")

@tool
def update_user_name(
    new_name: str,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Update user-name in short-term memory."""
    return Command(update={
        "user_name": new_name,
        "messages": [
            ToolMessage(f"Updated user name to {new_name}", tool_call_id=tool_call_id)
        ]
    })


model = ChatOpenAI(model="gpt-4.1",
                openai_api_key=os.getenv('OPENAI_API_KEY'),
                openai_api_base=os.getenv('OPENAI_API_BASE'),
                temperature=0)
# Example agent setup
agent = create_react_agent(
    model=model,
    tools=[get_user_name, update_user_name],
    state_schema=CustomState,
    checkpointer=memory,
)

if __name__ == '__main__':
    # Invocation: reads the name from state (initially empty)
    # agent.invoke({"messages": "what's my name?"})  # 简写方法
    config = {'configurable': {'thread_id': "testid_12345"}}
    response = agent.invoke({"messages": [{"role": "user", "content": "我的名字是 Alice"}]}, config=config)
    print(response)
    result_state = agent.invoke({"messages": {"role": "user", "content": "what's my name?"}}, config=config)
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

