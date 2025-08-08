#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/6 10:18
# @File  : inject_command_tool.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  : 计划的Agent，使用tool实现计划
import dotenv
import os
import json
import collections
from typing import Annotated, NotRequired
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from typing import Annotated
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool, InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
dotenv.load_dotenv()

memory = MemorySaver()

class CustomState(AgentState):
    # The user_name field in short-term state
    thread_id: NotRequired[str]

PLAN_STORAGE = collections.defaultdict(dict)
@tool
def plan_tool(action: str, config: RunnableConfig, payload: list[dict] = []) -> str:
    """
    Plan制作计划，当传入action为create和update必须提供payload参数。 get和list则不需要提供payload参数。
    - action: 'create', 'update', 'get', 'list'
    - payload: list[dict]，例如 [{"step1":"查询xxx"}, {"step2": "然后xxx"}]
    """
    print(f"plan_tool调用: 操作是：{action}, Payload是：{payload}")
    metadata = config.get("metadata", {})
    thread_id = metadata.get("thread_id")
    if not thread_id:
        return "缺少 thread_id"

    # 初始化存储
    has_plans = PLAN_STORAGE.setdefault(thread_id, {})

    # 尝试解析 payload
    if isinstance(payload, str):
        try:
            data = json.loads(payload) if payload else []
        except json.JSONDecodeError:
            return "无效的 payload 格式，应为 JSON 字符串。"
    elif isinstance(payload, list):
        data = payload
    else:
        return "无效的 payload 类型，应为字符串或列表。"

    # 不同 action 的处理逻辑
    if action == "create":
        for item in data:
            has_plans.update(item)
        return f"已创建 plan: {data}"

    elif action == "update":
        for item in data:
            has_plans.update(item)
        return f"已更新 plan: {data}"

    elif action == "get":
        if not data or not isinstance(data, list) or not isinstance(data[0], dict):
            return "get 操作需要 payload 中包含 key，例如 [{\"key\": \"step1\"}]"
        key = data[0].get("key")
        if not key:
            return "get 操作需要提供 key"
        content = has_plans.get(key)
        return f"{key} -> {content}" if content else f"Plan '{key}' 不存在。"

    elif action == "list":
        if not has_plans:
            return "暂无任何 plan。"
        return "\n".join(f"{k}: {v}" for k, v in has_plans.items())
    else:
        return f"未知的 action: {action}，支持：create/update/get/list。"



@tool
def web_search(query: str) -> str:
    """网络搜索"""
    return f"LangGraph核心技术概念，LangGraph和LangChain同宗同源，底层架构完全相同、接口完全相通。从开发者角度来说，LangGraph也是使用LangChain底层API来接入各类大模型、LangGraph也完全兼容LangChain内置的一系列工具。换而言之，LangGraph的核心功能都是依托LangChain来完成。但是和LangChain的链式工作流哲学完全不同的是，LangGraph的基础哲学是构建图结构的工作流，并引入“状态”这一核心概念来描绘任务执行情况，从而拓展了LangChain LCEL链式语法的功能灵活程度。"

@tool
def query_entity(entity: str) -> str:
    """查询实体解释"""
    return f"MemorySaver 是 LangGraph 的一个内存持久化工具，它依赖于以下配置项来正确工作，thread_id：唯一标识一个对话线程。checkpoint_ns：命名空间，用于组织不同的检查点。checkpoint_id：特定检查点的唯一标识符。"


model = ChatOpenAI(model="gpt-4.1",
                openai_api_key=os.getenv('OPENAI_API_KEY'),
                openai_api_base=os.getenv('OPENAI_API_BASE'),
                temperature=0)
# Example agent setup
agent = create_react_agent(
    model=model,
    tools=[plan_tool,web_search,query_entity],
    prompt="对于用户提出的问题，请先使用plan_tool列出计划，然后调用对应的工具完成整个任务",
    state_schema=CustomState,
    checkpointer=memory,
)

if __name__ == '__main__':
    # Invocation: reads the name from state (initially empty)
    config = {'configurable': {'thread_id': "testid_12345"}}
    result_state = agent.invoke({"messages": [{"role": "user", "content": "解释下LangGraph和MemorySaver"}]}, config=config)
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
