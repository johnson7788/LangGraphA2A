# -*- coding: utf-8 -*-
"""
PlanAgent（ADK LlmAgent）
- 接收用户目标文本，使用 PLAN_AGENT_PROMPT 生成结构化计划 JSON
- after_agent_callback：把 plan 写入 state['plan']，并将 phase 置为 EXECUTE
"""

import json
import re
from typing import Optional, Dict, Any
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai.types import GenerateContentConfig
from google.adk.agents.invocation_context import InvocationContext
from ...create_model import create_model
from ...config import PLAN_AGENT_CONFIG
from .prompt import PLAN_AGENT_PROMPT
import logging

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"```json\s*(?P<json>{.*?})\s*```", re.DOTALL | re.IGNORECASE)


def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    m = _JSON_BLOCK_RE.search(text)
    if m:
        try:
            return json.loads(m.group("json"))
        except Exception:
            pass
    first, last = text.find("{"), text.rfind("}")
    if first != -1 and last > first:
        try:
            return json.loads(text[first:last+1])
        except Exception:
            return None
    return None


def _after_agent_callback(callback_context: CallbackContext):
    # 聚合本次输出文本
    evt = callback_context._invocation_context.session.events[-1]
    parts = getattr(evt.content, "parts", []) or []
    text = "\n".join([getattr(p, "text", "") for p in parts if getattr(p, "text", None)]).strip()
    data = _extract_json(text) or {}

    state = callback_context.state or {}
    plan = data.get("plan")
    if plan:
        state["plan"] = plan
        state["phase"] = "EXECUTE"
    return None  # 不替换原响应

class PlanAgent(LlmAgent):
    """
    列出计划的Agent
    """
    def __init__(self, **kwargs):
        super().__init__(
            name="PlanAgent",
            model=create_model(PLAN_AGENT_CONFIG["model"], PLAN_AGENT_CONFIG["provider"]),
            description="把用户目标拆解为可执行计划（JSON）",
            instruction=PLAN_AGENT_PROMPT,
            tools=[],
            after_agent_callback=_after_agent_callback,
            generate_content_config=GenerateContentConfig(temperature=0.2),
            **kwargs
        )

    async def _run_async_impl(self, ctx: InvocationContext):
        # 并行跑子 agents（父类会执行并流式产出事件）
        logger.info(f"evaluation_novelty Agent开始工作，现有消息总数: {len(ctx.session.events)}")
        async for e in super()._run_async_impl(ctx):
            yield e

plan_agent = PlanAgent()