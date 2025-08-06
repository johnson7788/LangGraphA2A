# A2A 和Langgraph 多轮对话(langgraph控制记忆)
保持相同的task_id和contextId即可， 相同的contextId传入Langgraph的Memory,Memory根据thread_id判断是否是同一个用户
[langgraph_memory](..%2Fexample%2Flanggraph_memory)

使用History来控制记忆，代替Agent的Memory
[history_langgraph.py](..%2Fexample%2Fhistory_langgraph.py)

# tool Context vs tool State
google的 adk是tool context，tool可以读取和更改state中的信息
https://google.github.io/adk-docs/context/#the-different-types-of-context

langgraph是 tool state, tool可以读取和修改state中的信息
https://langchain-ai.github.io/langgraph/how-tos/tool-calling/#short-term-memory

# InjectedState 工具获取state中信息, 如果工具信息写入state，需要使用Command命令
```python
示例1:
from typing import Annotated, NotRequired
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState

class CustomState(AgentState):
    # The user_name field in short-term state
    user_name: NotRequired[str]

@tool
def get_user_name(
    state: Annotated[CustomState, InjectedState]
) -> str:
    """Retrieve the current user-name from state."""
    # Return stored name or a default if not set
    return state.get("user_name", "Unknown user")

# Example agent setup
agent = create_react_agent(
    model="anthropic:claude-3-7-sonnet-latest",
    tools=[get_user_name],
    state_schema=CustomState,
)

# Invocation: reads the name from state (initially empty)
agent.invoke({"messages": "what's my name?"})


示例2:
from typing_extensions import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

@tool
def my_tool(query: str, state: Annotated[dict, InjectedState]) -> str:
    info = state.get("user_info", {})
    return f"Hello, {info.get('name', 'guest')}!"

```

# InjectedToolCallId 返回的消息带上工具的id
```python
from typing import Annotated
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool, InjectedToolCallId

@tool
def update_user_name(
    new_name: str,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Update user-name in short-term memory."""
    return Command(update={
        "user_name": new_name,
        "messages": [
            ToolMessage(f"Updated user name to {new_name}", tool_call_id=tool_call_id)
        ]
    })
```

# Command 的主要作用
Command 是一种特殊返回值类型（返回对象），允许工具函数在执行结束后 显式地更新 LangGraph 的 graph state。
它替代了传统只返回文本的方式，使工具能够同时更新状态字段（如新增键）并发送消息给用户（通过 ToolMessage）；
本质上，是工具主动向 graph 注入 state 更新逻辑的接口。注意ToolMessage返回的数据格式，第一个参数content
```python
from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.types import Command

@tool
def human_assistance(
    name: str, birthday: str,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    # 调用 human-in-the‑loop 接口（interrupt），获取确认或修正
    ...  
    state_update = {
        "name": verified_name,
        "birthday": verified_birthday,
        "messages": [
            ToolMessage(response, tool_call_id=tool_call_id)
        ],
    }
    return Command(update=state_update)
tool_call_id 用 InjectedToolCallId 注入调用 ID；
在 update 字段中，你指定要插入/覆盖的 state keys，如 "name"、"birthday"；
同时，[ToolMessage] 可以用于添加聊天记录回执，由后续节点处理并展示给用户。
```


# MemorySaver 是 LangGraph 的一个内存持久化工具，它依赖于以下配置项来正确工作
thread_id：唯一标识一个对话线程。
checkpoint_ns：命名空间，用于组织不同的检查点。
checkpoint_id：特定检查点的唯一标识符。


# trim_messages 的作用与用法
trim_messages 是用来在消息过多导致上下文超限时，裁剪对话历史的工具，支持按 token 数或消息条数裁剪，常用配置如下：
strategy="last"：保留最后的消息。
token_counter=count_tokens_approximately：使用近似 token 计数函数，性能更快。
max_tokens=...：最大 token 限制。
start_on="human"：确保从用户消息开始。
end_on=("human","tool")：确保以用户或工具消息结束。
include_system=True：保留系统消息（如存在）。
allow_partial 可选：允许截断部分消息内容

# pre_model_hook 插入一个节点，每次调用 LLM 之前执行这个函数，对消息进行裁剪。
