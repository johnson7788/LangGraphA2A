# agent.py
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from dotenv import load_dotenv

from .sub_agents.plan_agent.agent import plan_agent
from .sub_agents.execute_agent.agent import parallel_dim_search_agent
from .sub_agents.summary_agent.agent import summary_agent

# 在模块顶部加载环境变量
load_dotenv('.env')


def _get_text_from_context(callback_context: CallbackContext) -> str | None:
    user_content = getattr(callback_context, "user_content", None)
    if user_content and getattr(user_content, "parts", None):
        for part in user_content.parts:
            text = getattr(part, "text", None)
            if text:
                return text
    return None


def before_agent_callback(callback_context: CallbackContext):
    """
    初始化：解析输入文本，初始化状态容器
    """
    state = callback_context.state
    metadata = state.get("metadata") or {}

    text = _get_text_from_context(callback_context)
    if not text:
        return types.Content(
            role="model",
            parts=[types.Part(text="请输入主题")]
        )
    state["question"] = text
    # ---------- 初始化容器 ---------
    # 工具搜索的结果
    state["references"] = {}      # tools.py 会持续写入 {file_id: {..., idx_val}}
    state["step_history"] = []    # 保留字段（兼容以前 Summary 模板）
    # Agent经过多次搜索后，觉得有用的结果
    state["search_results"] = {}  # 各Agent的搜索结果聚合

    return None

root_agent = SequentialAgent(
    name="SearchAgent",
    description="按照要求制定计划并实施（多维度并行搜索）",
    sub_agents=[plan_agent, parallel_dim_search_agent, summary_agent],
    before_agent_callback=before_agent_callback
)
