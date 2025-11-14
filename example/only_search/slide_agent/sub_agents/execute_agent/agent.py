# -*- coding: utf-8 -*-
"""
MultiDimSearchAgent（ParallelAgent）
- 读取 state.plan.dimensions
- 为每个维度动态创建一个 Llm 子Agent（可用 PaperSearch / AbstractSearch / WebSearch / DocumentSearch）
- 子Agent 输出 JSON，after 回调把有用结果汇总进 state['search_results'] & state['notes']（并沿用 state['references']）
"""

import json
import re
from pydantic import PrivateAttr
from typing import Optional, Dict, Any, List, AsyncGenerator
from google.adk.agents import ParallelAgent, BaseAgent
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.genai.types import GenerateContentConfig
from ...create_model import create_model
from ...config import EXECUTE_AGENT_CONFIG
from ..execute_agent.tools import PaperSearch, AbstractSearch
from .prompt import SEARCH_WORKER_PROMPT
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


class _SearchWorker(LlmAgent):
    """
    单维度检索 Worker；指令会动态注入该维度 JSON。
    产出严格 JSON，由 after 回调写回 state。
    """
    # 提供默认值，避免 pydantic 初始化时“没有这个属性”
    _dim: Dict[str, Any] = PrivateAttr(default=None)

    def __init__(self, dim: Dict[str, Any], **kwargs):
        # 先完成 pydantic / LlmAgent 的初始化
        super().__init__(
            name=f"SearchWorker_{dim.get('id','unknown')}",
            description=f"并行检索子Agent：{dim.get('name','')}",
            model=create_model(EXECUTE_AGENT_CONFIG["model"], EXECUTE_AGENT_CONFIG["provider"]),
            instruction=self._dyn_instruction,  # 这里晚点才会被调用
            tools=[PaperSearch, AbstractSearch],
            after_agent_callback=self._after_callback,
            generate_content_config=GenerateContentConfig(temperature=0.2),
            **kwargs
        )
        # 再设置私有属性，避免被 pydantic 初始化覆盖
        object.__setattr__(self, "_dim", dim)

    def _dyn_instruction(self, ctx: InvocationContext) -> str:
        # 把维度 JSON 注入提示词
        return SEARCH_WORKER_PROMPT + "\n[dimension]\n```json\n" + json.dumps(self._dim, ensure_ascii=False) + "\n```"

    @staticmethod
    def _after_callback(callback_context: CallbackContext):
        """
        汇总到：
        - state['search_results'][dimension_id] = {...子Agent JSON...}
        - state['notes'] 追加入维度级别的 notes
        references 的写入由工具层完成（tools.py 已经在 state['references'] 里维护）
        """
        evt = callback_context._invocation_context.session.events[-1]
        parts = getattr(evt.content, "parts", []) or []
        text = "\n".join([getattr(p, "text", "") for p in parts if getattr(p, "text", None)]).strip()
        data = _extract_json(text) or {}

        st = callback_context.state or {}
        dim_id = data.get("dimension_id", "unknown")
        if "search_results" not in st:
            st["search_results"] = {}
        st["search_results"][dim_id] = {
            "dimension_id": dim_id,
            "useful_docs": data.get("useful_docs", []),
            "summary_points": data.get("summary_points", []),
            "notes": data.get("notes", "")
        }
        return None


class MultiDimSearchAgent(ParallelAgent):
    """
    读取 plan.dimensions，动态构造并发子Agent，运行后将结果统一保存在 state['search_results']。
    """
    def __init__(self, **kwargs):
        # 先占位一个空的 sub_agents；真正的子 agent 在 run 时构建
        super().__init__(
            name="MultiDimSearchAgent",
            description="按 plan.dimensions 并行检索并回写 state",
            sub_agents=[],
            **kwargs
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator:
        st = ctx.session.state or {}
        plan = st.get("plan") or {}
        dims: List[Dict[str, Any]] = plan.get("dimensions") or []

        if not dims:
            logger.warning("MultiDimSearchAgent: plan.dimensions 为空，将直接返回。")
            return

        # 动态创建子 Agent
        self.sub_agents = [_SearchWorker(dim=d) for d in dims]

        # 清理历史事件，避免上下文过长
        logger.info(f"MultiDimSearchAgent 开始并行搜索，启动Agent数量: {len(self.sub_agents)}")
        ctx.session.events = []  # 保留最近少量上下文

        # 并行跑子 agents（父类会执行并流式产出事件）
        async for e in super()._run_async_impl(ctx):
            yield e

        # 并行完成后，做一次轻量聚合（可供 Summary 使用）
        st["phase"] = "SEARCH_DONE"
        return


parallel_dim_search_agent = MultiDimSearchAgent()
