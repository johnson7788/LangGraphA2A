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
    search_results = ctx.state.get("search_results", {})
    question = ctx.state.get("question", "")
    parts = []
    for _, agent_result in search_results.items():
        parts.append(json.dumps(agent_result, ensure_ascii=False))
    content = "\n".join(parts)
    prompt = SUMMARY_AGENT_PROMPT.format(question=question, search_results=content)
    return prompt


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
        logger.info(f"Summary Agent开始工作，现有消息总数: {len(ctx.session.events)}")
        ctx.session.events = []
        async for e in super()._run_async_impl(ctx):
            yield e

summary_agent = SummaryAgent()