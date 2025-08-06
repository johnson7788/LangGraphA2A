#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/6 10:18
# @File  : inject_command_tool.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 只用history传入，不用memory
import dotenv
import os
import json
from typing import Annotated, List, Optional
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from typing import Annotated
from langgraph.types import Command
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.messages.utils import trim_messages, count_tokens_approximately
dotenv.load_dotenv()

def pre_model_hook(state: AgentState):
    # 如果想截断历史，可在这里使用 trim_messages，例如：
    trimmed = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=2048,
        start_on="human",
        end_on=("human", "tool")
    )
    return {"llm_input_messages": trimmed}

@tool
def echo(input: str) -> str:
    """简单反回示例工具"""
    return f"[TOOL ECHO] {input}"

model = ChatOpenAI(model="gpt-4.1",
                openai_api_key=os.getenv('OPENAI_API_KEY'),
                openai_api_base=os.getenv('OPENAI_API_BASE'),
                temperature=0)
# Example agent setup
agent = create_react_agent(
    model=model,
    tools=[echo],
    pre_model_hook=pre_model_hook,
)

if __name__ == '__main__':
    history: List[HumanMessage | AIMessage] = [
        HumanMessage(content="你好,我是Johnson Guo"),
        AIMessage(content="你好，很高兴认识你, Johnson Guo"),
    ]
    history.append(HumanMessage(content="你知道我叫什么名字吗"))
    # 用 agent.invoke，手动传入完整 history
    result_state = agent.invoke({"messages": history})
    new_messages = result_state["messages"]  # 包含工具调用、AI 回复等
    for m in new_messages:
        print(f"{m.type}: {m.content}")

