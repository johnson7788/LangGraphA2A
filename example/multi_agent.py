#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/29 13:25
# @File  : multi_agent.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :
#!/usr/bin/env python
"""
一个可以直接运行的 LangGraph 多 Agent 示例（Supervisor 架构 + ReAct 子代理）。

运行前准备：
1) 安装依赖：
   pip install -U langchain langgraph langchain-openai langchain-core langgraph-supervisor

2) 配置环境变量（以 OpenAI 为例）：
   export OPENAI_API_KEY=你的OpenAIKey

运行：
   python langgraph_multi_agent_example.py
"""

from __future__ import annotations
import dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
dotenv.load_dotenv()

# =========================
# 工具：给子代理使用
# =========================
# MathAgent 的工具
@tool
def add(a: float, b: float) -> float:
    """Return a + b."""
    return a + b


@tool
def multiply(a: float, b: float) -> float:
    """Return a * b."""
    return a * b


@tool
def divide(a: float, b: float) -> float:
    """Return a / b. Raise if dividing by zero."""
    if b == 0:
        raise ValueError("Division by zero.")
    return a / b


# WriterAgent 的工具
@tool
def to_haiku(topic: str, number: float) -> str:
    """把一个数字结果写成三行中文俳句（含主题）。"""
    return f"{topic}之中\n数字如风掠过：{number}\n心声落纸间"


@tool
def polish(text: str, tone: str = "concise") -> str:
    """按照给定语气简单润色文本。"""
    return text if tone == "raw" else f"[{tone}] {text}"


# =========================
# 构建多 Agent 图（Supervisor 架构）
# =========================

def build_graph():
    # 子代理（ReAct）：数学助手
    math_agent = create_react_agent(
        model="openai:gpt-4o-mini",
        tools=[add, multiply, divide],
        prompt=(
            "You are MathAgent. Solve math precisely. "
            "Prefer using tools for calculations. "
            "When finished, include a line 'FINAL_ANSWER: <number>'."
        ),
        name="math_agent",
    )

    # 子代理（ReAct）：写作助手
    writer_agent = create_react_agent(
        model="openai:gpt-4o-mini",
        tools=[to_haiku, polish],
        prompt=(
            "You are WriterAgent. Turn results into short Chinese haiku or polished text. "
            "If you receive a numeric result from MathAgent, you may call to_haiku to craft a haiku. "
            "End your message with 'DONE'."
        ),
        name="writer_agent",
    )

    # 监督者：负责在子代理之间调度
    supervisor = create_supervisor(
        agents=[math_agent, writer_agent],
        model=ChatOpenAI(model="gpt-4o-mini"),
        prompt=(
            "You are the Supervisor.\n"
            "- Route tasks to the right agent.\n"
            "- For calculations, call math_agent first.\n"
            "- For prose/haiku/formatting, call writer_agent after math is done.\n"
            "- Keep delegating until the user's request is fully satisfied, then answer the user directly.\n"
            "- You may call agents multiple times if needed."
        ),
    ).compile()

    return supervisor


# =========================
# 演示
# =========================

def demo():
    graph = build_graph()
    user_msg = "请计算 (13*7)+42，然后把结果写成三行俳句，最后再给出最终数字。"

    print("=== USER ===")
    print(user_msg)

    print("\n=== STREAM (事件流) ===")
    for event in graph.stream({"messages": [{"role": "user", "content": user_msg}]}):
        # event 形如 {"supervisor": {...}} / {"math_agent": {...}} / {"writer_agent": {...}}
        print(event, "\n")

    print("\n=== FINAL ===")
    result = graph.invoke({"messages": [{"role": "user", "content": user_msg}]})
    final_msg = result["messages"][-1]
    # BaseMessage 兼容处理
    content = getattr(final_msg, "content", None) or final_msg.get("content")
    print(content)


if __name__ == "__main__":
    demo()
