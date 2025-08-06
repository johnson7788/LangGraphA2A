import os
from collections.abc import AsyncIterable
from typing import Any, Literal
from typing import Annotated, NotRequired
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from tools import search_document_db, search_personal_db, search_guideline_db
from langchain_core.messages.utils import trim_messages, count_tokens_approximately
from langgraph.checkpoint.memory import MemorySaver
from models import create_model
import dotenv
dotenv.load_dotenv()

#记忆是必须的
memory = MemorySaver()

def pre_model_hook(state: AgentState):
    trimmed = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=2048,
        start_on="human",
        end_on=("human", "tool")
    )
    return {"llm_input_messages": trimmed}

class ResponseFormat(BaseModel):
    """按照这个格式回答用户。"""

    status: Literal['completed', 'error'] = 'completed'
    message: str

class CustomState(AgentState):
    # The user_name field in short-term state
    structured_response: NotRequired[ResponseFormat]
    search_dbs: NotRequired[str]

class KnowledgeAgent:
    """知识库问答 Agent"""

    SYSTEM_INSTRUCTION = (
        "你是一个知识库问答助手。你的任务是：\n"
        "1. 根据用户提出的问题，确定合适的关键词；\n"
        "2. 调用工具（如 search_document_db、search_personal_db、search_guideline_db）搜索相应的知识库；\n"
        "3. 可以多次使用不同关键词不断检索，直到找到答案或明确无法找到信息；\n"
        "4. 对用户的问题进行准确、清晰的回答；\n"
        "5. 回答中可以说明你检索了哪些数据库和关键词，不过不要暴露工具内部实现。\n"
        "如果用户的问题超出知识库或工具范围，就礼貌告知无法处理该类型问题。"
    )

    FORMAT_INSTRUCTION = (
        "如果处理过程中发生错误，请将 status 设置为 'error'；\n"
        "如果请求成功完成，请将 status 设置为 'completed'。"
    )

    def __init__(self):
        self.model = create_model()
        self.tools = [search_document_db, search_personal_db, search_guideline_db]

        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=(self.FORMAT_INSTRUCTION, ResponseFormat),
            state_schema=CustomState,
            pre_model_hook=pre_model_hook
        )

    async def stream(self, query, context_id) -> AsyncIterable[dict[str, Any]]:
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id}}

        for item in self.graph.stream(inputs, config, stream_mode='values'):
            message = item['messages'][-1]
            print(f"Agent输出的message信息: {message}")
            current_state = self.graph.get_state(config)
            search_dbs = current_state.values.get("search_dbs")
            print(f"search_dbs: {search_dbs}")
            print(f"current_state.metadata: {current_state.metadata}")
            if isinstance(message, AIMessage) and message.tool_calls and len(message.tool_calls) > 0:
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': '正在检索相关知识…'
                }
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': '正在处理检索结果…'
                }

        yield self.get_agent_response(config)

    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        structured_response = current_state.values.get('structured_response')
        print(f"Agent输出:structured_response.message: {structured_response.message}")
        if structured_response and isinstance(structured_response, ResponseFormat):
            if structured_response.status == 'error':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message
                }
            if structured_response.status == 'completed':
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': structured_response.message
                }

        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': (
                '暂时无法处理您的请求，请稍后再试。'
            )
        }

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
