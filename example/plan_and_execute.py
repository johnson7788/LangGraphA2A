#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/29 11:52
# @File  : plan_and_execute.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :  Plan & Execute with logging

import os
import sys
import asyncio
import operator
import logging
from typing import Annotated, List, Tuple, Union

import dotenv
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

# LangChain / LangGraph
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END
from zai import ZhipuAiClient   # pip install zai-sdk
dotenv.load_dotenv()
# ============ Logging Setup ============
def setup_logging() -> logging.Logger:
    """
    Configure logging to stdout (and optionally to file).
    - LOG_LEVEL (env): DEBUG/INFO/WARNING/ERROR/CRITICAL (default INFO)
    - LOG_FILE  (env): if set, also write logs to this file.
    """
    level_name = os.getenv("LOG_LEVEL", "DEBUG").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger("plan_and_execute")
    logger.setLevel(level)
    logger.propagate = False  # avoid duplicate logs if root handlers exist

    # Clear existing handlers if re-run in the same interpreter
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    sh = logging.StreamHandler(stream=sys.stdout)
    sh.setLevel(level)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    log_file = os.getenv("LOG_FILE")
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # Quiet down noisy libs unless LOG_LEVEL is DEBUG
    noisy_level = logging.WARNING if level > logging.DEBUG else logging.DEBUG
    for noisy in ("httpx", "openai", "langchain", "asyncio"):
        logging.getLogger(noisy).setLevel(noisy_level)

    logger.debug("Logging initialized. Level=%s, File=%s", level_name, log_file or "(stdout only)")
    return logger

logger = setup_logging()


if "ZHIPU_API_KEY" not in os.environ:
    logger.warning("ZHIPU_API_KEY not found in environment. Web search will fail without it.")
else:
    logger.debug("ZHIPU_API_KEY detected.")

WebSearchClient = ZhipuAiClient(api_key=os.environ.get("ZHIPU_API_KEY"))


class WebSearchResult(BaseModel):
    url: str
    title: str
    snippet: str

async def search_web(keyword: str) -> List[WebSearchResult]:
    """
    真实的网络搜索函数
    """
    logger.info("WebSearch | query=%r", keyword)
    try:
        response = WebSearchClient.web_search.web_search(
            search_engine="search_std",
            search_query=keyword,
            count=15,  # 返回结果的条数，范围1-50，默认10
            search_recency_filter="noLimit",  # 搜索指定日期范围内的内容
            content_size="high"  # 控制网页摘要的字数，默认medium
        )
        items = response.get("search_result", []) or []
        logger.debug("WebSearch | received %d results", len(items))
        results = [
            WebSearchResult(
                url=item.get('url', ''),
                title=item.get('title', ''),
                snippet=item.get('content', '')
            ) for item in items
        ]
        logger.info("WebSearch | parsed %d results", len(results))
        return results
    except Exception as e:
        logger.exception("WebSearch | error during search: %s", e)
        return []

# ----------- 定义工具 -----------
tools = [search_web]

# ----------- 定义执行代理（ReAct Agent）-----------
agent_llm = ChatOpenAI(model="gpt-4o", temperature=0)
agent_prompt = "You are a helpful assistant."
agent_executor = create_react_agent(agent_llm, tools, prompt=agent_prompt)
logger.debug("Agent initialized with model=gpt-4o")

# ----------- 定义状态结构 -----------
class PlanExecute(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str

# ----------- 规划（Planner）-----------
class Plan(BaseModel):
    """未来要执行的计划"""
    steps: List[str] = Field(
        description="不同的步骤，按顺序排列。确保每步信息充分可独立执行。"
    )

planner_prompt = ChatPromptTemplate.from_messages(
    [
        ("system",
         "For the given objective, come up with a simple step by step plan. "
         "This plan should involve individual tasks, that if executed correctly will yield the correct answer. "
         "Do not add any superfluous steps. "
         "The result of the final step should be the final answer. "
         "Make sure that each step has all the information needed - do not skip steps."),
        ("placeholder", "{messages}"),
    ]
)

planner = planner_prompt | ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(Plan)
logger.debug("Planner initialized with structured output")

# ----------- 重规划 / 收尾（Re-planner / Decider）-----------
class Response(BaseModel):
    """最终面向用户的回答"""
    response: str

class Act(BaseModel):
    """下一步动作：要么直接回复，要么输出新计划"""
    action: Union[Response, Plan] = Field(
        description="If you want to respond to user, use Response. "
                    "If you need to further use tools to get the answer, use Plan."
    )

replanner_prompt = ChatPromptTemplate.from_template(
    """For the given objective, come up with a simple step by step plan. \
This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

Your objective was this:
{input}

Your original plan was this:
{plan}

You have currently done the follow steps:
{past_steps}

Update your plan accordingly. If no more steps are needed and you can return to the user, then respond with that. Otherwise, fill out the plan.
Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan."""
)

replanner = replanner_prompt | ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(Act)
logger.debug("Replanner initialized with structured output")

# ----------- 各节点实现（执行一步、规划、重规划、结束判断）-----------
async def execute_step(state: PlanExecute):
    """执行当前计划中的第 1 步，并把执行结果追加到 past_steps。"""
    plan = state.get("plan") or []
    if not plan:
        logger.info("ExecuteStep | no plan steps to execute")
        return {}

    plan_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
    task = plan[0]  # 取第一步
    logger.info("ExecuteStep | executing step 1: %s", task)
    # 每次都执行step1，因为我们的计划每次都会更新，即每次执行完成一步后，都会更新剩余计划，然后进行下一步操作
    task_formatted = (
        f"For the following plan:\n{plan_str}\n\n"
        f"You are tasked with executing step 1, {task}."
    )
    try:
        agent_response = await agent_executor.ainvoke({"messages": [("user", task_formatted)]})
        content = agent_response["messages"][-1].content
        logger.debug("ExecuteStep | agent response received (len=%d)", len(content) if content else 0)
        return {
            "past_steps": [(task, content)],
        }
    except Exception as e:
        logger.exception("ExecuteStep | error invoking agent: %s", e)
        return {"past_steps": [(task, f"[ERROR] {e}")]}

async def plan_step(state: PlanExecute):
    """根据用户输入生成初始计划。"""
    logger.info("Planner | start planning for input: %r", state.get("input"))
    try:
        plan = await planner.ainvoke({"messages": [("user", state["input"])]})
        logger.info("Planner | generated %d step(s)", len(plan.steps))
        logger.debug("Planner | steps: %s", plan.steps)
        return {"plan": plan.steps}
    except Exception as e:
        logger.exception("Planner | error generating plan: %s", e)
        return {"plan": []}

async def replan_step(state: PlanExecute):
    """根据已完成步骤，决定：继续给出剩余计划，或直接产出最终回复。"""
    logger.info("Replanner | deciding next action (done_steps=%d)", len(state.get("past_steps", [])))
    try:
        output = await replanner.ainvoke(state)
        if isinstance(output.action, Response):
            logger.info("Replanner | produced final response")
            return {"response": output.action.response}
        else:
            logger.info("Replanner | produced updated plan with %d step(s)", len(output.action.steps))
            logger.debug("Replanner | new steps: %s", output.action.steps)
            return {"plan": output.action.steps}
    except Exception as e:
        logger.exception("Replanner | error during replanning: %s", e)
        return {"response": f"[ERROR] {e}"}

def should_end(state: PlanExecute):
    """若已有最终 response，则结束；否则继续交回 agent 执行下一步。"""
    if state.get("response"):
        logger.info("Graph | should_end -> END (final response present)")
        return END
    else:
        logger.debug("Graph | should_end -> agent (continue executing)")
        return "agent"

# ----------- 构建 LangGraph 并编译 -----------
def build_app():
    logger.debug("Graph | building StateGraph")
    workflow = StateGraph(PlanExecute)
    workflow.add_node("planner", plan_step)
    workflow.add_node("agent", execute_step)
    workflow.add_node("replan", replan_step)

    workflow.add_edge(START, "planner")     # 起点 -> 规划
    workflow.add_edge("planner", "agent")   # 规划 -> 执行
    workflow.add_edge("agent", "replan")    # 执行 -> 重规划/收尾
    workflow.add_conditional_edges(
        "replan",
        should_end,
        ["agent", END],                     # 继续执行 或 结束
    )
    compiled = workflow.compile()
    logger.debug("Graph | compiled successfully")
    return compiled

# ----------- 运行入口 -----------
async def main():
    try:
        logger.info("=== App starting ===")
        app = build_app()
        query = "2025年苹果有哪些新品发布?"
        logger.info("Run | query=%r", query)

        config = {"recursion_limit": 50}

        # 流式查看每一步
        async for event in app.astream({"input": query}, config=config):
            for k, v in event.items():
                if k != "__end__":
                    # v 可能较大，这里只打印键及类型/长度信息
                    summary = v
                    logger.info("StreamEvent | node=%s | %s", k, summary)

        logger.info("=== App finished ===")
    except Exception as e:
        logger.exception("Fatal | unhandled exception: %s", e)
        raise

if __name__ == "__main__":
    asyncio.run(main())
