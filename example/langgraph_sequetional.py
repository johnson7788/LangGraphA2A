#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/29 16:10
# @File  : langgraph_sequetional.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :

from __future__ import annotations
import os
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv
from typing_extensions import TypedDict, NotRequired
from langgraph.managed import RemainingSteps
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AnyMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from zai import ZhipuAiClient  # pip install zai-sdk
# ========== 环境变量 ==========
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("请在 .env 中设置 OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
WebSearchClient = ZhipuAiClient(api_key=os.environ.get("ZHIPU_API_KEY"))


# ========== 共享 LLM & 工具 ==========
llm = ChatOpenAI(model=MODEL, temperature=0)
def web_search(keyword: str, max_results: int = 20):
    """实际上调用的是 Zhipu 的通用 Web 搜索；名称沿用原始实现。"""
    try:
        response = WebSearchClient.web_search.web_search(
            search_engine="search_std",
            search_query=keyword,
            count=min(max_results, 15),
            search_recency_filter="noLimit",
            content_size="high",
        )
        items = response.get("search_result", []) or []
        return items
    except Exception as e:
        return []


# ========== 定义图状态（使用 add_messages 归约器） ==========
class AgentState(TypedDict):
    # LangGraph 将根据该注解把新消息正确地追加/更新到历史中
    messages: Annotated[list[AnyMessage], add_messages]
    remaining_steps: NotRequired[RemainingSteps]


# ========== 定义两个预置 ReAct Agent ==========
# 提示词可用 prompt=（较新版本），如遇版本差异报错，可改为 state_modifier=
reader_agent = create_react_agent(
    model=llm,
    tools=[web_search],
    prompt=(
        "你是资料检索与阅读助手。根据用户问题检索网络并给出要点，"
        "必要时调用搜索工具，输出要简洁、包含来源线索。"
    ),
    state_schema=AgentState,
)

organizer_agent = create_react_agent(
    model=llm,
    tools=[web_search],  # 若不需要再次检索，可传空列表 []
    prompt=(
        "你是信息整理助手。基于当前对话消息，将上一步的发现归纳为结构化输出："
        "包含【结论】【关键依据】【可操作建议】三部分，尽量编号列出。"
    ),
    state_schema=AgentState,
)

# ========== 将两个 Agent 封装为节点函数 ==========
def run_reader(state: AgentState) -> AgentState:
    # 直接把 {"messages": [...]} 状态交给子图执行
    result = reader_agent.invoke(state)
    return {"messages": result["messages"]}

def run_organizer(state: AgentState) -> AgentState:
    result = organizer_agent.invoke(state)
    return {"messages": result["messages"]}

# ========== 构建顺序图 ==========
workflow = StateGraph(AgentState)
workflow.add_node("reader", run_reader)
workflow.add_node("organizer", run_organizer)
workflow.add_edge(START, "reader")
workflow.add_edge("reader", "organizer")
workflow.add_edge("organizer", END)

# 可选：为同一 thread_id 提供多轮对话记忆
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# ========== 运行示例 ==========
if __name__ == "__main__":
    user_q = "给我一份‘西班牙夏季旅行城市’的要点清单并归纳成行程建议"

    # 首次调用：传入 HumanMessage 列表即可
    init_state: AgentState = {"messages": [HumanMessage(content=user_q)]}

    # thread_id 用于记忆：同一 ID 将在多次调用间共享状态
    config = {"configurable": {"thread_id": "demo-thread"}}

    # 简单一次性调用（也可用 .stream 观察逐步事件）
    result = app.invoke(init_state, config=config)

    print("\n==== 输出（按消息顺序）====\n")
    for msg in result["messages"]:
        role = getattr(msg, "type", "unknown").upper()
        content = getattr(msg, "content", str(msg))
        print(f"{role}: {content}\n")

    # 再次提问可复用同一 thread_id，图会记住上下文：
    # next_state = {"messages": [HumanMessage(content="把结论压缩成100字摘要")]}
    # result2 = app.invoke(next_state, config=config)