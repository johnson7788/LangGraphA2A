# 整个执行流程
a2a_client.py --> main.py(uvicorn) --> agent_executor.py(execute函数) -->agent.py(stream函数)

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

# 工具变化，增多，减少等，Agent必须重新初始化

# 配置模型的代理
model = ChatOpenAI(
    model=os.getenv('LLM_MODEL'),
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    temperature=0,
    openai_proxy="http://127.0.0.1:7890"
)

# LangGraph Agent的响应模式
invoke表示一次性返回结果
result_state = agent.invoke({"messages": message})

你要在你给出的 ReACT agent 示例中启用 LangGraph 的 streaming 模式，只需要使用 `stream`（同步）或 `astream`（异步）接口，并指定不同的 `stream_mode`。下面是如何修改你的脚本来实现流式返回的方式：

---

## 🛠 在 ReACT agent 中使用 streaming

下面展示了如何在你的代码基础上使用三种常用的流式模式：

```python
inputs = {"messages": [HumanMessage(content="你好啊，介绍下什么是LangGraph")]}
```

### ✅ “updates” 模式 — 流式输出每个节点的状态更新

```python
for chunk in agent.stream(inputs, stream_mode="updates"):
    print(chunk)
```

* 每当 ReACT agent 的一个节点（如 LLM 请求、工具调用、最终回答等）执行结束时，返回该节点的更新部分。适合追踪 agent 的执行步骤。([langchain-ai.github.io][1], [博客园][2])

### ✅ “values” 模式 — 流式输出每个节点后的完整状态快照

```python
for chunk in agent.stream(inputs, stream_mode="values"):
    print(chunk)
```

* 每次节点执行完后，返回整个 graph 的完整 state 对象。适合需要全局状态追踪的场景。([DEV Community][3], [CSDN][4])

### ✅ “messages” 模式 — 流式输出 LLM 的 token 级输出

```python
for token, metadata in agent.stream(inputs, stream_mode="messages"):
    print(token)
```

* 逐 token 输出 GPT-4 或其他 LLM 的内容，适合即时显示模型正在“思考”的过程。([LangChain][5], [langchain-ai.github.io][1])

---

## 📌 支持多种模式组合

你也可以同时使用多个模式，例如同时获取节点更新和 token 流输出：

```python
for mode, data in agent.stream(inputs, stream_mode=["updates", "messages"]):
    if mode == "messages":
        token, metadata = data
        print("token:", token)  # LLM 输出
    else:  # mode == "updates"
        print("update:", data)
```

* 这种方式能同时展示 agent 执行逻辑和内容输出。([CSDN][4], [langchain-ai.github.io][1])

---

## ⚙ 与你代码结合示例

```python
if __name__ == '__main__':
    inputs = {"messages": [HumanMessage(content="你好啊，介绍下什么是LangGraph")]}
    for chunk in agent.stream(inputs, stream_mode=["updates", "messages"]):
        print(chunk)
```

* 如果你使用异步环境，则使用 `await agent.astream(inputs, stream_mode=...)`。

---

## 📚 总结对比

| 模式         | 输出形式                          | 典型用途               |
| ---------- | ----------------------------- | ------------------ |
| `updates`  | 每步节点更新（节点名 + 返回值）             | 查看 agent 执行过程，节省带宽 |
| `values`   | 每步完整 Graph state 快照           | 审计或调试全局状态          |
| `messages` | LLM Model 的 token-by-token 输出 | 提升对话交互的实时感         |


# curl作为客户端测试
curl -N -X POST http://localhost:10000/ \
  -H "Content-Type: application/json" \
  -d '{
    "id": "c1635d3e-7cd5-4965-a615-14ed8fb28842",
    "jsonrpc": "2.0",
    "method": "message/stream",
    "params": {
      "message": {
        "kind": "message",
        "messageId": "f4181ef28c3a421a9284c633d27ccbcf",
        "metadata": {
          "language": "English"
        },
        "parts": [
          {
            "kind": "text",
            "text": "帕金森的治疗方案有哪些？"
          }
        ],
        "role": "user"
      }
    }
  }'

# 流式输出，这里也需要改成流式的
async for item in self.graph.astream(inputs, config, stream_mode='values'):
