import os
import time
from collections import defaultdict
import json
from collections.abc import AsyncIterable
from typing import Any, Literal,Dict
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.prebuilt import create_react_agent
from tools import search_document_db, search_personal_db, search_guideline_db
from langchain_core.messages.utils import trim_messages, count_tokens_approximately
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from models import create_model
from custom_state import CustomState, ResponseFormat
import dotenv
dotenv.load_dotenv()

#记忆是必须的
memory = MemorySaver()

def pre_model_hook(state: AgentState):
    trimmed = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=4096,
        start_on="human",
        end_on=("human", "tool")
    )
    return {"llm_input_messages": trimmed}


def load_mcp_servers(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    servers_config = config.get("mcpServers", {})
    servers: Dict[str, Any] = {}

    for name, entry in servers_config.items():
        if entry.get("disabled", False):
            continue

        if entry.get("transport") == "stdio":
            servers[name] = {
                "command": entry["command"],
                "args": entry.get("args", []),
                "env": entry.get("env", {}),
                "transport": "stdio"
            }
        else:
            servers[name] = {
                "url": entry["url"],
                "transport": entry["transport"]
            }

    return servers


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
    def __init__(self, mcp_config=None):
        self.model = create_model()
        self.mcp_config = mcp_config
        self.tools = [search_document_db, search_personal_db, search_guideline_db]
        self.graph = None  # 等异步初始化完才赋值

    async def ainit(self):
        if self.mcp_config and os.path.exists(self.mcp_config):
            print(f"提供了mcp_config，开始加载mcp_config: {self.mcp_config}")
            mcp_config_tools = load_mcp_servers(config_path=self.mcp_config)
            client = MultiServerMCPClient(mcp_config_tools)
            tools = await client.get_tools()
            self.tools.extend(tools)
        print(f"LLM可用的工具总数是: {len(self.tools)}")

        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=(self.FORMAT_INSTRUCTION, ResponseFormat),
            state_schema=CustomState,
            pre_model_hook=pre_model_hook
        )
        print(f"初始化graph： {self.graph}")
        return self  # 方便链式调用
    async def stream(self, query, history, context_id) -> AsyncIterable[dict[str, Any]]:
        """
        调用langgraph 处理用户的请求，并流式的返回
        Args:
            query:  str: 问题
            history: list: 历史记录，可以传入或者不传入，如果context_id相同，也不会对已有的langgraph的MemorySaver影响
            context_id:
        Returns:
        """
        # 塑造历史记录
        if self.graph is None:
            await self.ainit()
        history = [
            HumanMessage(content=msg['content']) if msg['role'] in ['human','user']
            else AIMessage(content=msg['content'])
            for msg in history
        ]
        # 添加当前的用户的问题
        history.append(HumanMessage(content=query))
        # 创建langgraph的输入
        inputs = {"messages": history}
        config = {'configurable': {'thread_id': context_id}}
        tool_chunks = []
        metadata = {}
        print(f"self.graph： {self.graph}")
        async for token, response_metadata in self.graph.astream(inputs, config, stream_mode='messages'):
            content = token.content or ""
            print(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
            print(f"Agent输出的message信息: {content}")
            current_state = self.graph.get_state(config)
            search_dbs = current_state.values.get("search_dbs")
            # 作为metadata发送给前端
            metadata = {"search_dbs": search_dbs}
            print(f"search_dbs: {search_dbs}")
            print(f"current_state.metadata: {current_state.metadata}")
            tool_call_chunks = token.additional_kwargs.get("tool_calls", [])
            # 收集工具调用分片
            if tool_call_chunks:
                print(f"收集了工具的分块的输出: {tool_call_chunks}")
                tool_chunks.extend(tool_call_chunks)
                continue

            # 处理普通 token 输出
            if content:
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': content,
                    'metadata': metadata,
                    'data_type': 'text_chunk'
                }

            # 如果检测到工具调用已经结束
            if "finish_reason" in token.response_metadata and token.response_metadata[
                "finish_reason"] == "tool_calls":
                merged_calls = defaultdict(lambda: {
                    "args": "",
                    "name": None,
                    "type": None,
                    "id": None
                })

                for chunk in tool_chunks:
                    index = chunk.get("index", 0)
                    merged = merged_calls[index]
                    merged["args"] += chunk.get("function", {}).get("arguments", "")
                    merged["name"] = chunk.get("function", {}).get("name", "") or merged["name"]
                    merged["type"] = chunk.get("type") or merged["type"]
                    merged["id"] = chunk.get("id") or merged["id"]

                final_tool_calls = []
                for idx in sorted(merged_calls.keys()):
                    info = merged_calls[idx]
                    try:
                        arguments_obj = json.loads(info["args"])
                    except json.JSONDecodeError:
                        arguments_obj = info["args"]

                    call = {
                        "index": idx,
                        "id": info["id"],
                        "type": info["type"],
                        "function": {
                            "name": info["name"],
                            "arguments": arguments_obj
                        }
                    }
                    final_tool_calls.append(call)

                # 获取工具调用前的状态信息
                current_state = self.graph.get_state(config)
                search_dbs = current_state.values.get("search_dbs")
                metadata = {"search_dbs": search_dbs}

                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': '正在使用tool检索相关知识…',
                    'metadata': metadata,
                    'data': final_tool_calls,
                    'data_type': 'tool_call'
                }
                tool_chunks.clear()

        # 最终响应（处理 structured_response）
        yield self.get_agent_response(config, metadata)

    def get_agent_response(self, config, metadata):
        # 自己组装的metadata信息，用于返回给前端
        current_state = self.graph.get_state(config)
        structured_response = current_state.values.get('structured_response')
        print(f"Agent输出:structured_response.message: {structured_response.message}")
        if structured_response and isinstance(structured_response, ResponseFormat):
            if structured_response.status == 'error':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                    'metadata': metadata,
                    'data_type': 'require_user'
                }
            if structured_response.status == 'completed':
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': structured_response.message,
                    'metadata': metadata,
                    'data_type': 'result'
                }

        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': '暂时无法处理您的请求，请稍后再试。',
            'metadata': metadata,
            'data_type': 'error'
        }

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
