# -*- coding: utf-8 -*-
"""
SummaryAgent（ADK LlmAgent）
- 把 state.plan 与 state.step_history 注入到提示词上下文，使模型按模板生成 Markdown 汇总
"""

import json
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.genai.types import GenerateContentConfig
from ...create_model import create_model
from ...config import SUMMARY_AGENT_CONFIG
from .prompt import SUMMARY_AGENT_PROMPT
import logging

logger = logging.getLogger(__name__)

def _dynamic_instruction(ctx: InvocationContext) -> str:
    plan = ctx.state.get("plan", {})
    history = ctx.state.get("step_history", [])
    log_events = ctx.state.get("log", [])

    plan_json = json.dumps(plan, ensure_ascii=False)
    history_json = json.dumps(history, ensure_ascii=False)
    log_json = json.dumps(log_events, ensure_ascii=False)

    prefix = SUMMARY_AGENT_PROMPT
    context = f"\n[plan]\n```json\n{plan_json}\n```\n[step_history]\n```json\n{history_json}\n```\n[log]\n```json\n{log_json}\n```\n"
    return prefix + context


class SummaryAgent(LlmAgent):
    """
    列出计划的Agent
    """
    def __init__(self, **kwargs):
        super().__init__(
            name="SummaryAgent",
            description="根据 plan 与 step_history 生成 Markdown 汇总",
            model=create_model(SUMMARY_AGENT_CONFIG["model"], SUMMARY_AGENT_CONFIG["provider"]),
            instruction=_dynamic_instruction,
            tools=[],
            generate_content_config=GenerateContentConfig(temperature=0.2),
            **kwargs
        )

    async def _run_async_impl(self, ctx: InvocationContext):
        # 并行跑子 agents（父类会执行并流式产出事件）
        logger.info(f"evaluation_novelty Agent开始工作，现有消息总数: {len(ctx.session.events)}")
        async for e in super()._run_async_impl(ctx):
            yield e

summary_agent = SummaryAgent()