#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/29 11:52
# @File  : plan_and_execute.py.py
# @Author: johnson
# @Contact : github: johnson7788
# @Desc  :

import os
import asyncio
import operator
from typing import Annotated, List, Tuple, Union
import dotenv
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
# LangChain / LangGraph
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END
from zai import ZhipuAiClient   #pip install zai-sdk
dotenv.load_dotenv()

WebSearchClient = ZhipuAiClient(api_key=os.environ["ZHIPU_API_KEY"])


class WebSearchResult(BaseModel):
    url: str
    title: str
    snippet: str

async def search_web(keyword: str) -> List[WebSearchResult]:
    """
    真实的网络搜索函数
    """
    response = WebSearchClient.web_search.web_search(
        search_engine="search_std",
        search_query=keyword,
        count=15,  # 返回结果的条数，范围1-50，默认10
        search_recency_filter="noLimit",  # 搜索指定日期范围内的内容
        content_size="high"  # 控制网页摘要的字数，默认medium
    )
    return [
        WebSearchResult(
            url=item['url'],
            title=item['title'],
            snippet=item['content']
        ) for item in response['search_result']
    ]

# ----------- 定义工具 -----------
tools = [search_web]


# ----------- 定义执行代理（ReAct Agent）-----------
# 教程中用 ChatOpenAI + create_react_agent 作为执行每一步任务的 agent
# 你也可以更换为其他支持的模型，如 "gpt-4o-mini"
agent_llm = ChatOpenAI(model="gpt-4o", temperature=0)
agent_prompt = "You are a helpful assistant."
agent_executor = create_react_agent(agent_llm, tools, prompt=agent_prompt)


# ----------- 定义状态结构 -----------
# plan: 当前计划（步骤列表）
# past_steps: 已执行的步骤及结果（累加）
# response: 若已得到最终回答，则在这里输出
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

# 使用结构化输出拿到 Plan(steps=[...])
planner = planner_prompt | ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(Plan)


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


# ----------- 各节点实现（执行一步、规划、重规划、结束判断）-----------
async def execute_step(state: PlanExecute):
    """执行当前计划中的第 1 步，并把执行结果追加到 past_steps。"""
    plan = state["plan"]
    if not plan:
        return {}

    plan_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
    task = plan[0]  # 取第一步
    task_formatted = (
        f"For the following plan:\n{plan_str}\n\n"
        f"You are tasked with executing step 1, {task}."
    )
    agent_response = await agent_executor.ainvoke({"messages": [("user", task_formatted)]})
    # 记录本步执行的“任务与结果”
    return {
        "past_steps": [(task, agent_response["messages"][-1].content)],
    }

async def plan_step(state: PlanExecute):
    """根据用户输入生成初始计划。"""
    print(f"开始生成计划，输入: {state}")
    plan = await planner.ainvoke({"messages": [("user", state["input"])]})
    print(f"输出生成的计划: {plan}")
    return {"plan": plan.steps}

async def replan_step(state: PlanExecute):
    """根据已完成步骤，决定：继续给出剩余计划，或直接产出最终回复。"""
    output = await replanner.ainvoke(state)
    if isinstance(output.action, Response):
        return {"response": output.action.response}
    else:
        return {"plan": output.action.steps}

def should_end(state: PlanExecute):
    """若已有最终 response，则结束；否则继续交回 agent 执行下一步。"""
    if "response" in state and state["response"]:
        return END
    else:
        return "agent"


# ----------- 构建 LangGraph 并编译 -----------
def build_app():
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
    return workflow.compile()


# ----------- 运行入口 -----------
async def main():
    app = build_app()
    # 你可以替换这里的 query
    query = "2025年苹果有哪些新品发布?"

    # 直接得到最终状态（包含最终回答）
    config = {"recursion_limit": 50}
    # final_state = await app.ainvoke({"input": query}, config=config)
    # print("\n=== Final Answer ===")
    # print(final_state.get("response") or "(no final response)")

    # 也可以选择流式查看每一步（如需，取消注释以下代码）
    async for event in app.astream({"input": query}, config=config):
        for k, v in event.items():
            if k != "__end__":
                print(v)


if __name__ == "__main__":
    asyncio.run(main())
