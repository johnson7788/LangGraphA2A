# -*- coding: utf-8 -*-
"""
FixPlanAgent（ADK LlmAgent）
- 读取 state.plan / state.step_history / state.last_failure / state.log / state.needs_fix
- 当 needs_fix 为 True 时，要求模型输出 {"patch":[...]} 或 {"plan":{...}}
- after_agent_callback 负责应用变更（优先 patch，若返回 plan 则全量替换）
- 若无需修复（needs_fix=False 或无失败上下文），则 NOOP（不更改 state）
"""

import json
from typing import List, Dict, Any
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from google.genai.types import GenerateContentConfig
from ....create_model import create_model
from ....config import PLAN_AGENT_CONFIG  # 复用同一提供商/模型或自定义
from .prompt import FIX_PLAN_AGENT_PROMPT

def _dynamic_instruction(ctx: InvocationContext) -> str:
    st = ctx.state or {}
    if not st.get("needs_fix"):
        # 无需修复时，给出一个可让模型输出空 JSON 的最小上下文
        return FIX_PLAN_AGENT_PROMPT + "\n[context]\n```json\n{\"noop\": true}\n```"

    plan = st.get("plan", {})
    history = st.get("step_history", [])
    last_failure = st.get("last_failure", {})
    log_events = st.get("log", [])

    payload = {
        "plan": plan,
        "step_history": history,
        "last_failure": last_failure,
        "log": log_events
    }
    return FIX_PLAN_AGENT_PROMPT + "\n[context]\n```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"


def _apply_patch(plan: Dict[str, Any], patch: List[Dict[str, Any]]) -> Dict[str, Any]:
    """极简 patch 应用器：支持 remove / replace / insert_before / insert_after / append"""
    if not plan:
        plan = {"steps": []}
    steps = list(plan.get("steps", []))
    index_by_id = {s.get("id"): i for i, s in enumerate(steps)}

    def insert_at(idx: int, new_steps: List[Dict[str, Any]]):
        for offset, s in enumerate(new_steps):
            steps.insert(idx + offset, s)

    for op in patch or []:
        typ = op.get("op")
        if typ == "remove":
            sid = op.get("id")
            i = index_by_id.get(sid)
            if i is not None:
                steps.pop(i)
                index_by_id = {s.get("id"): i for i, s in enumerate(steps)}
        elif typ == "replace":
            sid = op.get("id")
            new_step = op.get("step")
            i = index_by_id.get(sid)
            if i is not None and isinstance(new_step, dict):
                steps[i] = new_step
                index_by_id = {s.get("id"): i for i, s in enumerate(steps)}
        elif typ == "insert_before":
            before_id = op.get("before_id")
            new_steps = op.get("steps", [])
            i = index_by_id.get(before_id)
            if i is not None and new_steps:
                insert_at(i, new_steps)
                index_by_id = {s.get("id"): i for i, s in enumerate(steps)}
        elif typ == "insert_after":
            after_id = op.get("after_id")
            new_steps = op.get("steps", [])
            i = index_by_id.get(after_id)
            if i is not None and new_steps:
                insert_at(i + 1, new_steps)
                index_by_id = {s.get("id"): i for i, s in enumerate(steps)}
        elif typ == "append":
            new_steps = op.get("steps", [])
            if new_steps:
                steps.extend(new_steps)
                index_by_id = {s.get("id"): i for i, s in enumerate(steps)}

    plan["steps"] = steps
    return plan


def _after_agent_callback(callback_context: CallbackContext):
    st = callback_context.state or {}
    # 若无需修复（被 before 拦截为 {}），这里不会更改任何状态
    if not st.get("needs_fix"):
        return None

    # 取本次模型输出文本
    evt = callback_context._invocation_context.session.events[-1]
    parts = getattr(evt.content, "parts", []) or []
    text = "\n".join([getattr(p, "text", "") for p in parts if getattr(p, "text", None)]).strip()

    data = {}
    try:
        data = json.loads(text)
    except Exception:
        # 非法 JSON：记录并跳过
        st["log"].append({"event": "fix_plan_error", "raw": text})
        return None

    new_plan = data.get("plan")
    patch = data.get("patch")

    if new_plan:
        st["plan"] = new_plan
        st["log"].append({"event": "fix_plan", "mode": "replace"})
    elif patch:
        st["plan"] = _apply_patch(st.get("plan", {}), patch)
        st["log"].append({"event": "fix_plan", "mode": "patch", "ops": len(patch)})
    else:
        st["log"].append({"event": "fix_plan_noop"})

    # 修复后清理标记
    st["needs_fix"] = False
    st["last_failure"] = None
    return None


def _before_agent_callback(callback_context: CallbackContext):
    """
    如果没有需要修复的标记，直接跳过（返回一个最小 JSON，让 LLM 不被调用）
    返回Content或者None，如果不需要修复，返回Content，如果需要修复，返回None
    """
    st = callback_context.state or {}
    if not st.get("needs_fix", False):
        # 返回一个空 JSON 响应，等价于“本轮不执行修复”
        return types.Content(parts=[types.Part(text="{}")])
    return None


fix_plan_agent = LlmAgent(
    name="FixPlanAgent",
    description="当执行失败/阻塞时，自动修订 plan（输出 plan 或 patch）",
    model=create_model(PLAN_AGENT_CONFIG["model"], PLAN_AGENT_CONFIG["provider"]),
    instruction=_dynamic_instruction,
    tools=[],
    before_agent_callback=_before_agent_callback,   # ←按需跳过Agent执行
    after_agent_callback=_after_agent_callback,
    generate_content_config=GenerateContentConfig(temperature=0.2),
)
