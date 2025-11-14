# -*- coding: utf-8 -*-
"""
ExecuteLoopAgent（ADK LoopAgent）
- StepExecuteSubAgent（LlmAgent）：按当前 step 执行，输出 step_result，并在 after 回调标记 needs_fix 等状态
- FixPlanAgent：当 needs_fix=True 时修复 plan；当 needs_fix=False 时由 before 回调跳过
- ExecuteControllerAgent（BaseAgent）：根据上一步状态推进 current_step_index 或终止 Loop
"""

import json
import re
from typing import Optional, Dict, Any, List, AsyncGenerator
from google.genai import types
from google.adk.events import Event, EventActions
from google.adk.agents import LoopAgent, BaseAgent
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.genai.types import GenerateContentConfig
from ...create_model import create_model
from ...config import EXECUTE_AGENT_CONFIG
from .prompt import EXECUTE_AGENT_PROMPT
from .tools import PaperSearch, WebSearch
import logging

# 复用你已有的 FixPlanAgent（已在其模块中支持“按需跳过”）
from .fix_plan_agent.agent import fix_plan_agent

logger = logging.getLogger(__name__)

# === 子 Agent 工具 ===

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


# ========== 1) 真正执行的子 Agent ==========

def _decide_replan(step_result: Dict[str, Any]) -> bool:
    status = (step_result or {}).get("status", "success")
    if status in ("failed", "blocked"):
        return True
    notes = (step_result or {}).get("notes", "").lower()
    return any(k in notes for k in ["need extra", "缺少", "补充", "依赖未满足"])


def _after_execute_callback(callback_context: CallbackContext):
    """
    累计 step_history；并在失败/阻塞时设置 needs_fix=True, last_failure=sr
    同时记录 last_step_status 供控制器使用
    """
    # 1) 取本次模型输出
    evt = callback_context._invocation_context.session.events[-1]
    parts = getattr(evt.content, "parts", []) or []
    text = "\n".join([getattr(p, "text", "") for p in parts if getattr(p, "text", None)]).strip()
    data = _extract_json(text) or {}

    state = callback_context.state or {}

    # 2) 累积 step_history
    sr = data.get("step_result")
    if not sr:
        state["last_step_status"] = None
        return None
    history: List[dict] = state.get("step_history", [])
    history.append(sr)
    state["step_history"] = history
    state["last_step_status"] = sr.get("status")
    state["last_step_id"] = sr.get("step_id")

    # 3) 失败/阻塞 → 打标，交给 FixPlanAgent
    if _decide_replan(sr):
        state["needs_fix"] = True
        state["last_failure"] = sr
        state["log"].append({
            "event": "need_fix_plan",
            "reason": sr.get("notes", "need update"),
            "step_id": sr.get("step_id"),
            "status": sr.get("status")
        })
    else:
        state["needs_fix"] = False  # 本步成功则清理

    return None


class StepExecuteSubAgent(LlmAgent):
    def __init__(self, **kwargs):
        super().__init__(
            name="StepExecuteSubAgent",
            description="按当前 step 调用工具并返回 step_result（JSON）",
            model=create_model(EXECUTE_AGENT_CONFIG["model"], EXECUTE_AGENT_CONFIG["provider"]),
            instruction=self._dyn_instruction,
            tools=[PaperSearch,WebSearch],
            after_agent_callback=_after_execute_callback,
            generate_content_config=GenerateContentConfig(temperature=0.2),
            **kwargs
        )

    async def _run_async_impl(self, ctx: InvocationContext):
        # 并行跑子 agents（父类会执行并流式产出事件）
        logger.info(f"StepExecuteSubAgent开始工作，现有消息总数: {len(ctx.session.events)}")
        ctx.session.events = ctx.session.events[:-3] #取后3个消息就行了，要不太多了
        async for e in super()._run_async_impl(ctx):
            yield e
    def _dyn_instruction(self, ctx: InvocationContext) -> str:
        st = ctx.state or {}
        plan = st.get("plan") or {}
        steps: List[Dict[str, Any]] = plan.get("steps") or []
        idx = int(st.get("current_step_index", 0))
        if idx < 0 or idx >= len(steps):
            # 越界：给最小上下文，ExecuteAgent 会返回 blocked
            return EXECUTE_AGENT_PROMPT + "\n[step]\n```json\n{}\n```"
        step = steps[idx]
        return EXECUTE_AGENT_PROMPT + "\n[step]\n```json\n" + json.dumps(step, ensure_ascii=False) + "\n```"


# ========== 2) 控制推进/终止的 Agent ==========
class ControllerAgent(BaseAgent):
    """
    决策：
    - 若 last_step_status == success：推进 current_step_index
    - 若 failed/blocked：不推进，下一轮让 FixPlanAgent 修补后重试本步
    - 若 current_step_index >= len(steps)：终止 Loop（escalate），转 Summary
    """
    def __init__(self, **kwargs):
        super().__init__(
            name="ExecuteControllerAgent",
            description="根据上一步状态推进或终止执行循环",
            **kwargs
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        st = ctx.session.state or {}
        plan = st.get("plan") or {}
        steps: List[Dict[str, Any]] = plan.get("steps") or []

        idx = int(st.get("current_step_index", 0))
        last_status = st.get("last_step_status")

        # 若越界或为空 → 直接终止
        if not steps or idx >= len(steps):
            # 没有可执行步骤，或已完成所有步骤
            yield Event(author=self.name, actions=EventActions(escalate=True))
            return

        if last_status == "success":
            # 推进到下一步
            st["current_step_index"] = idx + 1
            st["last_step_status"] = None  # 清理本轮标记

        # 终止判断：推进后是否结束
        new_idx = int(st.get("current_step_index", 0))
        if new_idx >= len(steps):
            # 所有步骤完成，允许进入总结
            st["phase"] = "SUMMARY"
            yield Event(author=self.name, actions=EventActions(escalate=True))
            return

        # 其余情况（首次进入 / 失败待修复 / 修复后需重试）：不做额外动作，交给下一轮 Loop
        return


# ========== 3) Loop 入口 ==========
def _before_loop_callback(callback_context: CallbackContext):
    """
    Loop 启动前的一次性初始化
    """
    st = callback_context.state or {}
    st["needs_fix"] = False
    st["last_step_status"] = None
    return None


execute_loop_agent = LoopAgent(
    name="ExecuteLoopAgent",
    max_iterations=500,  # 给足量，依赖控制器来终止
    sub_agents=[
        StepExecuteSubAgent(),   # 1) 执行当前步骤
        fix_plan_agent,          # 2) 失败/阻塞时修复（无需修复则跳过）
        ControllerAgent() # 3) 推进/终止
    ],
    before_agent_callback=_before_loop_callback,
)
