import os
import time
from collections import defaultdict
import json
from collections.abc import AsyncIterable
from typing import Any, Literal,Dict
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.prebuilt import create_react_agent
from tools import search_document_db,search_personal_db,search_guideline_db
from langchain_core.messages.utils import trim_messages, count_tokens_approximately
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from models import create_model
from custom_state import CustomState
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
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    def __init__(self, mcp_config=None, select_tool_names=["search_document_db", "search_personal_db", "search_guideline_db"]):
        """
        初始化Agent
        Args:
            mcp_config: mcp工具
            select_tool_names: 内置的可选工具
        """
        self.default_select_tool_names = select_tool_names
        self.model = create_model()
        self.mcp_config = mcp_config
        select_tools = []
        for tool_name in select_tool_names:
            if tool_name in ["search_document_db", "search_personal_db", "search_guideline_db"]:
                select_tools.append(eval(tool_name))
            else:
                select_tools.append(tool_name)
        self.tools = select_tools
        tool_names = '、'.join(select_tool_names)
        self.SYSTEM_INSTRUCTION = """
你是一位擅长应对复杂问题的医学助手，具备高级推理能力和信息检索能力。你的任务是理解并拆解用户的问题，积极调用搜索工具获取足够高质量的信息，再进行全面、准确、可信的回答。
    请严格遵循以下规则：
    1. 深度理解问题：理解用户提出的问题核心，可在必要时进行分解、重构或澄清，确保回答覆盖全部用户关心的点；
    2. 充分使用多个搜索工具{tool_names}，你可以多轮搜索，直到获取充分、权威且相关的信息，避免仅基于初步结果回答；
    3. 高质量整合：结合搜索内容，使用你自己的语言输出结构清晰、信息全面、有逻辑支撑的答案，不要只复述资料，而应体现归纳、比较和推理能力；
    4. 坦诚应对不确定性：如果在检索中找不到明确答案，应如实说明，并基于现有信息提出合理推测、分析路径或建议；
    5. 标注引用来源：在使用搜索工具后，需要在涉及引用信息的句末，使用Markdown脚注格式标注出处，如：“该方法已被某个研究验证[^02-772-2]。”
    6. 鼓励详细阐述：回答时应尽量详尽，包括背景信息、可能的多种观点或方法、优缺点分析等，避免简略回答或仅下结论。
    7. 可以不用输出markdown的段落之间的分割线。
    8. 不要在回答结束时列出所有参考的引用来源。
        """
        self.graphes = {} # 等异步初始化完才赋值

    async def create_graph(self, tool_names=[], mcp_urls=[]):
        """
        创建graph,并传入合适的tools
        Args:
            tool_names: list[str], 如果为空，表示使用所有工具
            mcp_urls: list[dict], 可以添加自定义的mcp工具, [{"name": "websearch", "url": "http://127.0.0.1:8300/sse"}]
        Returns:
        """
        select_tools = []
        if tool_names == []:
            tool_names = self.default_select_tool_names
            print(f"传入的tool_names为空，使用默认所有工具： {tool_names}")
        for tool_name in tool_names:
            select_tools.append(eval(tool_name))
        if self.mcp_config and os.path.exists(self.mcp_config):
            print(f"提供了mcp_config，开始加载mcp_config: {self.mcp_config}")
            mcp_config_tools = load_mcp_servers(config_path=self.mcp_config)
            client = MultiServerMCPClient(mcp_config_tools)
            tools = await client.get_tools()
            select_tools.extend(tools)
        print(f"LLM可用的工具总数是: {len(self.tools)}")

        SYSTEM_INSTRUCTION = self.SYSTEM_INSTRUCTION.format(tool_names=tool_names)
        graph = create_react_agent(
            self.model,
            tools=select_tools,
            checkpointer=memory,
            prompt=SYSTEM_INSTRUCTION,
            state_schema=CustomState,
            pre_model_hook=pre_model_hook
        )
        print(f"初始化graph： {graph}")
        return graph
    async def stream(self, query, history, context_id, tools=[], user_id="") -> AsyncIterable[dict[str, Any]]:
        """
        调用langgraph 处理用户的请求，并流式的返回
        Args:
            query:  str: 问题
            history: list: 历史记录，可以传入或者不传入，如果context_id相同，也不会对已有的langgraph的MemorySaver影响
            context_id:
            tools: list[str]，使用那些工具，如果为[]，表示使用所有工具
            user_id：用户id，用于知识库问答
        Returns:
        """
        # 塑造历史记录
        if self.graphes.get(context_id) is None:
            self.graphes[context_id] = await self.create_graph(tool_names=tools)
        graph_instance = self.graphes[context_id]
        history = [
            HumanMessage(content=msg['content']) if msg['role'] in ['human','user']
            else AIMessage(content=msg['content'])
            for msg in history
        ]
        # 添加当前的用户的问题
        history.append(HumanMessage(content=query))
        # 创建langgraph的输入
        inputs = {"messages": history, "user_id":user_id}
        config = {'configurable': {'thread_id': context_id}}
        tool_chunks = []
        metadata = {}
        print(f"graph_instance： {graph_instance}")
        async for token, response_metadata in graph_instance.astream(inputs, config, stream_mode='messages'):
            content = token.content or ""
            print(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()))
            print(f"Agent输出的message信息: {content}")
            current_state = graph_instance.get_state(config)
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

            if isinstance(token, ToolMessage):
                # 工具的输出结果
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': '正在使用tool检索相关知识…',
                    'metadata': metadata,
                    'data': [{'name': token.name, 'tool_call_id': token.tool_call_id, 'tool_output': content}],
                    'data_type': 'tool_response'
                }
            elif isinstance(token, AIMessage) and content:
                # 处理普通 token 输出
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': content,
                    'metadata': metadata,
                    'data_type': 'text_chunk'
                }

            # 如果检测到工具调用已经结束
            if "finish_reason" in token.response_metadata and token.response_metadata["finish_reason"] == "tool_calls":
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
                current_state = graph_instance.get_state(config)
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

        # 最终响应（处理 messages）
        yield self.get_agent_response(token, config, metadata, graph_instance)

    def get_agent_response(self, token, config, metadata, graph_instance):
        # 自己组装的metadata信息，用于返回给前端
        current_state = graph_instance.get_state(config)
        print(f"最后一轮次Agent输出 token: {token}")
        finish_reason = token.response_metadata["finish_reason"]
        if finish_reason == 'stop':
            return {
                'is_task_complete': True,
                'require_user_input': False,
                'content': token.content,
                'metadata': metadata,
                'data_type': 'result'
            }
        else:
            return {
                'is_task_complete': False,
                'require_user_input': True,
                'content': '发生了错误！暂时无法处理您的请求，请稍后再试,错误：' + token.content,
                'metadata': metadata,
                'data_type': 'error'
            }
