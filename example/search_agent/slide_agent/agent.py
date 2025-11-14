# agent.py
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from dotenv import load_dotenv
# 创新发现循环Agent
from google.adk.agents.sequential_agent import SequentialAgent
from .sub_agents.plan_agent.agent import plan_agent
from .sub_agents.execute_agent.agent import execute_loop_agent
from .sub_agents.summary_agent.agent import summary_agent

# 在模块顶部加载环境变量
load_dotenv('.env')


def _get_text_from_context(callback_context: CallbackContext) -> str | None:
    """拿到用户刚发来的纯文本。"""
    user_content = getattr(callback_context, "user_content", None)
    if user_content and getattr(user_content, "parts", None):
        for part in user_content.parts:
            text = getattr(part, "text", None)
            if text:
                return text
    return None


def before_agent_callback(callback_context: CallbackContext):
    """
    初始化：从文本解析 topic/description，并读取 metadata 里的配置（如 num_innovations / years / research_mode 等）。
    """
    state = callback_context.state
    metadata = state.get("metadata") or {}

    text = _get_text_from_context(callback_context)
    if not text:
        return types.Content(
            role="model",
            parts=[types.Part(text="请输入主题")]
        )

    # ---------- 元数据解析 ---------
    state["references"] = {}
    # 每个步骤的历史
    state["step_history"] = []
    state["log"] = []
    state["current_step_index"] = 0

    return None


root_agent = SequentialAgent(
    name="SearchAgent",
    description="按照要求制定计划并实施",
    sub_agents=[plan_agent, execute_loop_agent, summary_agent],
    before_agent_callback=before_agent_callback
)
