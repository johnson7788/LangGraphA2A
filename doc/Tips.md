# 整个执行流程
a2a_client.py --> main.py(uvicorn) --> agent_executor.py(execute函数) -->agent.py(stream函数)

# A2A 和Langgraph 多轮对话(langgraph控制记忆)
用LangGraph的MemorySaver 保持相同的task_id和contextId即可， 相同的contextId传入Langgraph的Memory,Memory根据thread_id判断是否是同一个用户
[langgraph_memory](..%2Fexample%2Flanggraph_memory)

使用History来控制记忆，代替Agent的Memory
[history_langgraph.py](..%2Fexample%2Fhistory_langgraph.py)

# A2A中如何和Langgraph的Agent传入hisotory
A2A 协议并没有针对“history 历史聊天记录”做专门定义或格式，我们在metadata中添加1个history字段，来进行历史记录的处理，然后交个langgraph记录到记忆中

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

# pre_model_hook用法
插入一个节点，每次调用 LLM 之前执行这个函数，对消息进行裁剪。

# 工具变化，增多，减少等，Agent必须重新初始化。

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
cd backend/knowledge_agent
python main.py
python a2a_client_single.py
输出示例:
```
Headers({'accept': '*/*', 'accept-encoding': 'gzip, deflate, zstd', 'connection': 'keep-alive', 'user-agent': 'python-httpx/0.28.1'})
=== 流式响应 示例 ===
2025/08/07 16:34:14
{'id': '93abcc32-62ae-48a6-ab70-8ee16d08912f', 'jsonrpc': '2.0', 'result': {'contextId': '91754423-0369-4d8e-96b3-4cc65a6d0e2a', 'history': [{'contextId': '91754423-0369-4d8e-96b3-4cc65a6d0e2a', 'kind': 'message', 'messageId': '01b4dd442be140cd9ebe55c38b29ce44', 'metadata': {'language': 'English'}, 'parts': [{'kind': 'text', 'text': '帕金森的治疗方案有哪些？'}], 'role': 'user', 'taskId': '5cdc4260-1d21-4a64-ab9c-e43e9de7e74d'}], 'id': '5cdc4260-1d21-4a64-ab9c-e43e9de7e74d', 'kind': 'task', 'status': {'state': 'submitted'}}}
2025/08/07 16:34:17
{'id': '93abcc32-62ae-48a6-ab70-8ee16d08912f', 'jsonrpc': '2.0', 'result': {'contextId': '91754423-0369-4d8e-96b3-4cc65a6d0e2a', 'final': False, 'kind': 'status-update', 'status': {'message': {'contextId': '91754423-0369-4d8e-96b3-4cc65a6d0e2a', 'kind': 'message', 'messageId': '46fa5e5b-6c70-4115-99e5-2118ebf1b967', 'metadata': {'search_dbs': []}, 'parts': [{'data': {'data': [{'name': 'search_guideline_db', 'args': {'query': '帕金森 治疗方案'}, 'id': 'call_NadSSF0juwc5l7YH0ngllmYi', 'type': 'tool_call'}, {'name': 'search_document_db', 'args': {'query': '帕金森病 治疗方法'}, 'id': 'call_lnyWUpKsGAZywX5AyIY9QjS8', 'type': 'tool_call'}, {'name': 'search_personal_db', 'args': {'query': '帕金森 治疗'}, 'id': 'call_PAemRB06NFIWMRABfJaW1tOV', 'type': 'tool_call'}]}, 'kind': 'data'}], 'role': 'agent', 'taskId': '5cdc4260-1d21-4a64-ab9c-e43e9de7e74d'}, 'state': 'working', 'timestamp': '2025-08-07T08:34:17.066649+00:00'}, 'taskId': '5cdc4260-1d21-4a64-ab9c-e43e9de7e74d'}}
2025/08/07 16:34:17
{'id': '93abcc32-62ae-48a6-ab70-8ee16d08912f', 'jsonrpc': '2.0', 'result': {'contextId': '91754423-0369-4d8e-96b3-4cc65a6d0e2a', 'final': False, 'kind': 'status-update', 'status': {'message': {'contextId': '91754423-0369-4d8e-96b3-4cc65a6d0e2a', 'kind': 'message', 'messageId': 'b1c4f0ae-1962-4ab9-bce1-971c1cccc14d', 'metadata': {'search_dbs': [{'db': 'search_guideline_db', 'result': [{'title': 'MDS 2025：治疗运动波动的循证综述', 'snippet': '官方推荐多种药物与手术选项用于改善 levodopa 相关起伏。', 'content': '2025 年 5 月 MDS 更新基于 Cochrane 与 GRADE 方法，对 levodopa 延释剂、pramipexole（速释与长效）、ropinirole、rotigotine、opicapone、safinamide、双侧 STN DBS 等评为“有效”；连续肠道 levodopa 输注、皮下 apomorphine、rasagiline、istradefylline、amantadine 延释剂、Zonisamide、GPI DBS 等评为“可能有效”用于 motor fluctuations。', 'source': 'Movement Disorders (MDS EBM Review)', 'timestamp': '2025‑05'}, {'title': 'FDA 批准 adaptive DBS（闭环深部脑刺激，aDBS）', 'snippet': '首个可根据脑电信号自动调节的 DBS 系统获 FDA 批准。', 'content': '美国 FDA 于 2025 年批准 Medtronic 的 BrainSense Adaptive aDBS 系统，这种闭环设备可持续监测桥臂核的异常脑电信号，并即时调节电刺激，相比传统 DBS 可减少 40% 电能用量，改善 tremor 与肌肉僵硬，并支持算法切换以优化响应并降低副作用。', 'source': 'UCSF 公告 / Medical News', 'timestamp': '2025‑02'}, {'title': 'Onapgo 药物输注治疗 motor fluctuations', 'snippet': 'FDA 批准皮下输注 apomorphine，用于显著 “off” 时间的患者。', 'content': '2025 年 2 月 FDA 批准 Onapgo（apomorphine HCl）连续皮下注射输注疗法，适用于经历明显 motor fluctuations 或 off-time 的帕金森患者。输注系统可持续提供较稳定的血药浓度，迅速缓解 tremor 与运动迟缓，成为 levodopa 波动管理的重要补充治疗手段。', 'source': 'Michael J. Fox 基金会新闻', 'timestamp': '2025‑02‑04'}]}, {'db': 'search_document_db', 'result': [{'title': 'CuATSM 恢复 SOD1 功能：小鼠病症逆转研究', 'snippet': '在帕金森小鼠模型中，用 CuATSM 递送铜可防止神经退化，显著改善运动能力。', 'content': '研究由悉尼大学领导，27 只小鼠进行剂量探索后确立15\u202fmg/kg 为最佳剂量；之后对10 只帕金森样模型连续用药3 个月。治疗组运动能力保持稳定，多巴胺神经元在黑质得到保护，而对照组出现神经退化与运动恶化。CuATSM 恢复了 SOD1 抗氧化功能，预防自由基损伤，从而阻止疾病进展。', 'source': 'Wired 报道', 'timestamp': '2025‑07‑10'}, {'title': 'MLi‑2 抑制 LRRK2：促进神经纤毛再生与神经保护', 'snippet': 'MLi‑2 在 LRRK2 突变型小鼠中，再生纤毛，恢复细胞通信并提升神经保护。', 'content': '斯坦福团队对 LRRK2 高活性基因突变小鼠施用 MLi‑2，共持续3 个月；结果显示 striatum 中神经和神经胶质细胞的初级纤毛数量恢复至健康水平，神经信号传递增强，多巴胺突触密度翻倍，提示可能逆转病理性功能损害。', 'source': 'Wired 报道', 'timestamp': '2025‑07‑10'}, {'title': 'Tavapadon 新药：TEMPO\u202f3\u202f期临床数据', 'snippet': '腾博登（tavapadon）靶向 D1/D5 受体，延长“on time”，不良反应少。', 'content': 'TEMPO 3 试验结果显示，tavapadon 每日口服一次可延长患者的运动控制“on time”，且诱发幻觉、血压变化等不良事件明显少于传统 levodopa；该药可用于早期或与 levodopa 联用治疗中晚期患者，正在申请 FDA 批准阶段。', 'source': 'NY Post / AAN 大会报告', 'timestamp': '2025‑04‑18'}]}]}, 'parts': [{'data': {'name': 'search_personal_db', 'tool_call_id': 'call_PAemRB06NFIWMRABfJaW1tOV', 'content': '[\n  {\n    "title": "笔记：GLP‑1 类药物在帕金森中的神经保护潜力",\n    "snippet": "记录 lixisenatide 在临床中延缓症状的初步结果。",\n    "content": "2024 年法国 NS‑Park 网络试验中，156 名最近确诊患者接受 lixisenatide 治疗，组内 motor score 恶化比率显著低于安慰剂组，但部分有恶心、呕吐等副作用；结合 FT 报道指出 GLP‑1 激动剂（如 Mounjaro, Wegovy）正在扩展研究至帕金森对于神经炎症和神经保护的潜在作用。",\n    "created": "2025‑06‑30"\n  },\n  {\n    "title": "康复训练笔记：Rock Steady Boxing 对情绪与运动改善",\n    "snippet": "总结 RSB 对抑郁和运动症状的双重益处。",\n    "content": "依据 arXiv 2024 报告，40 名参与者接受为期 8 周每周两次的 Rock Steady Boxing，Beck 抑郁评分逐步下降，运动表现也有所改善；虽然有 6 人中途退出，但结果强调持续运动训练对改善非运动症状的效果。",\n    "created": "2025‑07‑15"\n  },\n  {\n    "title": "实验药 Solengepras（CVN‑424）阶段Ⅲ进展记录",\n    "snippet": "GPR6 逆激动剂全口服小分子，进入 III 期临床。",\n    "content": "Cerevance 开发的 Solengepras（CVN‑424）为 GPR6 逆激动剂，口服给药，2025 年初已进入 III 期试验阶段，动物模型显示能改善运动能力，未来可能作为 levodopa 替代或辅助疗法。",\n    "created": "2025‑05‑20"\n  }\n]'}, 'kind': 'data'}], 'role': 'agent', 'taskId': '5cdc4260-1d21-4a64-ab9c-e43e9de7e74d'}, 'state': 'working', 'timestamp': '2025-08-07T08:34:17.076644+00:00'}, 'taskId': '5cdc4260-1d21-4a64-ab9c-e43e9de7e74d'}}
2025/08/07 16:34:17
{'id': '93abcc32-62ae-48a6-ab70-8ee16d08912f', 'jsonrpc': '2.0', 'result': {'contextId': '91754423-0369-4d8e-96b3-4cc65a6d0e2a', 'final': False, 'kind': 'status-update', 'status': {'message': {'contextId': '91754423-0369-4d8e-96b3-4cc65a6d0e2a', 'kind': 'message', 'messageId': '1acd57fd-0608-4d73-bdb8-93e89f2a3518', 'metadata': {'search_dbs': [{'db': 'search_guideline_db', 'result': [{'title': 'MDS 2025：治疗运动波动的循证综述', 'snippet': '官方推荐多种药物与手术选项用于改善 levodopa 相关起伏。', 'content': '2025 年 5 月 MDS 更新基于 Cochrane 与 GRADE 方法，对 levodopa 延释剂、pramipexole（速释与长效）、ropinirole、rotigotine、opicapone、safinamide、双侧 STN DBS 等评为“有效”；连续肠道 levodopa 输注、皮下 apomorphine、rasagiline、istradefylline、amantadine 延释剂、Zonisamide、GPI DBS 等评为“可能有效”用于 motor fluctuations。', 'source': 'Movement Disorders (MDS EBM Review)', 'timestamp': '2025‑05'}, {'title': 'FDA 批准 adaptive DBS（闭环深部脑刺激，aDBS）', 'snippet': '首个可根据脑电信号自动调节的 DBS 系统获 FDA 批准。', 'content': '美国 FDA 于 2025 年批准 Medtronic 的 BrainSense Adaptive aDBS 系统，这种闭环设备可持续监测桥臂核的异常脑电信号，并即时调节电刺激，相比传统 DBS 可减少 40% 电能用量，改善 tremor 与肌肉僵硬，并支持算法切换以优化响应并降低副作用。', 'source': 'UCSF 公告 / Medical News', 'timestamp': '2025‑02'}, {'title': 'Onapgo 药物输注治疗 motor fluctuations', 'snippet': 'FDA 批准皮下输注 apomorphine，用于显著 “off” 时间的患者。', 'content': '2025 年 2 月 FDA 批准 Onapgo（apomorphine HCl）连续皮下注射输注疗法，适用于经历明显 motor fluctuations 或 off-time 的帕金森患者。输注系统可持续提供较稳定的血药浓度，迅速缓解 tremor 与运动迟缓，成为 levodopa 波动管理的重要补充治疗手段。', 'source': 'Michael J. Fox 基金会新闻', 'timestamp': '2025‑02‑04'}]}, {'db': 'search_document_db', 'result': [{'title': 'CuATSM 恢复 SOD1 功能：小鼠病症逆转研究', 'snippet': '在帕金森小鼠模型中，用 CuATSM 递送铜可防止神经退化，显著改善运动能力。', 'content': '研究由悉尼大学领导，27 只小鼠进行剂量探索后确立15\u202fmg/kg 为最佳剂量；之后对10 只帕金森样模型连续用药3 个月。治疗组运动能力保持稳定，多巴胺神经元在黑质得到保护，而对照组出现神经退化与运动恶化。CuATSM 恢复了 SOD1 抗氧化功能，预防自由基损伤，从而阻止疾病进展。', 'source': 'Wired 报道', 'timestamp': '2025‑07‑10'}, {'title': 'MLi‑2 抑制 LRRK2：促进神经纤毛再生与神经保护', 'snippet': 'MLi‑2 在 LRRK2 突变型小鼠中，再生纤毛，恢复细胞通信并提升神经保护。', 'content': '斯坦福团队对 LRRK2 高活性基因突变小鼠施用 MLi‑2，共持续3 个月；结果显示 striatum 中神经和神经胶质细胞的初级纤毛数量恢复至健康水平，神经信号传递增强，多巴胺突触密度翻倍，提示可能逆转病理性功能损害。', 'source': 'Wired 报道', 'timestamp': '2025‑07‑10'}, {'title': 'Tavapadon 新药：TEMPO\u202f3\u202f期临床数据', 'snippet': '腾博登（tavapadon）靶向 D1/D5 受体，延长“on time”，不良反应少。', 'content': 'TEMPO 3 试验结果显示，tavapadon 每日口服一次可延长患者的运动控制“on time”，且诱发幻觉、血压变化等不良事件明显少于传统 levodopa；该药可用于早期或与 levodopa 联用治疗中晚期患者，正在申请 FDA 批准阶段。', 'source': 'NY Post / AAN 大会报告', 'timestamp': '2025‑04‑18'}]}, {'db': 'search_personal_db', 'result': [{'title': '笔记：GLP‑1 类药物在帕金森中的神经保护潜力', 'snippet': '记录 lixisenatide 在临床中延缓症状的初步结果。', 'content': '2024 年法国 NS‑Park 网络试验中，156 名最近确诊患者接受 lixisenatide 治疗，组内 motor score 恶化比率显著低于安慰剂组，但部分有恶心、呕吐等副作用；结合 FT 报道指出 GLP‑1 激动剂（如 Mounjaro, Wegovy）正在扩展研究至帕金森对于神经炎症和神经保护的潜在作用。', 'created': '2025‑06‑30'}, {'title': '康复训练笔记：Rock Steady Boxing 对情绪与运动改善', 'snippet': '总结 RSB 对抑郁和运动症状的双重益处。', 'content': '依据 arXiv 2024 报告，40 名参与者接受为期 8 周每周两次的 Rock Steady Boxing，Beck 抑郁评分逐步下降，运动表现也有所改善；虽然有 6 人中途退出，但结果强调持续运动训练对改善非运动症状的效果。', 'created': '2025‑07‑15'}, {'title': '实验药 Solengepras（CVN‑424）阶段Ⅲ进展记录', 'snippet': 'GPR6 逆激动剂全口服小分子，进入 III 期临床。', 'content': 'Cerevance 开发的 Solengepras（CVN‑424）为 GPR6 逆激动剂，口服给药，2025 年初已进入 III 期试验阶段，动物模型显示能改善运动能力，未来可能作为 levodopa 替代或辅助疗法。', 'created': '2025‑05‑20'}]}]}, 'parts': [{'data': {'name': 'search_personal_db', 'tool_call_id': 'call_PAemRB06NFIWMRABfJaW1tOV', 'content': '[\n  {\n    "title": "笔记：GLP‑1 类药物在帕金森中的神经保护潜力",\n    "snippet": "记录 lixisenatide 在临床中延缓症状的初步结果。",\n    "content": "2024 年法国 NS‑Park 网络试验中，156 名最近确诊患者接受 lixisenatide 治疗，组内 motor score 恶化比率显著低于安慰剂组，但部分有恶心、呕吐等副作用；结合 FT 报道指出 GLP‑1 激动剂（如 Mounjaro, Wegovy）正在扩展研究至帕金森对于神经炎症和神经保护的潜在作用。",\n    "created": "2025‑06‑30"\n  },\n  {\n    "title": "康复训练笔记：Rock Steady Boxing 对情绪与运动改善",\n    "snippet": "总结 RSB 对抑郁和运动症状的双重益处。",\n    "content": "依据 arXiv 2024 报告，40 名参与者接受为期 8 周每周两次的 Rock Steady Boxing，Beck 抑郁评分逐步下降，运动表现也有所改善；虽然有 6 人中途退出，但结果强调持续运动训练对改善非运动症状的效果。",\n    "created": "2025‑07‑15"\n  },\n  {\n    "title": "实验药 Solengepras（CVN‑424）阶段Ⅲ进展记录",\n    "snippet": "GPR6 逆激动剂全口服小分子，进入 III 期临床。",\n    "content": "Cerevance 开发的 Solengepras（CVN‑424）为 GPR6 逆激动剂，口服给药，2025 年初已进入 III 期试验阶段，动物模型显示能改善运动能力，未来可能作为 levodopa 替代或辅助疗法。",\n    "created": "2025‑05‑20"\n  }\n]'}, 'kind': 'data'}], 'role': 'agent', 'taskId': '5cdc4260-1d21-4a64-ab9c-e43e9de7e74d'}, 'state': 'working', 'timestamp': '2025-08-07T08:34:17.078373+00:00'}, 'taskId': '5cdc4260-1d21-4a64-ab9c-e43e9de7e74d'}}
2025/08/07 16:34:34
{'id': '93abcc32-62ae-48a6-ab70-8ee16d08912f', 'jsonrpc': '2.0', 'result': {'artifact': {'artifactId': '1de9ef8a-f89a-4af4-816c-11c55572d7df', 'metadata': {'search_dbs': [{'db': 'search_guideline_db', 'result': [{'title': 'MDS 2025：治疗运动波动的循证综述', 'snippet': '官方推荐多种药物与手术选项用于改善 levodopa 相关起伏。', 'content': '2025 年 5 月 MDS 更新基于 Cochrane 与 GRADE 方法，对 levodopa 延释剂、pramipexole（速释与长效）、ropinirole、rotigotine、opicapone、safinamide、双侧 STN DBS 等评为“有效”；连续肠道 levodopa 输注、皮下 apomorphine、rasagiline、istradefylline、amantadine 延释剂、Zonisamide、GPI DBS 等评为“可能有效”用于 motor fluctuations。', 'source': 'Movement Disorders (MDS EBM Review)', 'timestamp': '2025‑05'}, {'title': 'FDA 批准 adaptive DBS（闭环深部脑刺激，aDBS）', 'snippet': '首个可根据脑电信号自动调节的 DBS 系统获 FDA 批准。', 'content': '美国 FDA 于 2025 年批准 Medtronic 的 BrainSense Adaptive aDBS 系统，这种闭环设备可持续监测桥臂核的异常脑电信号，并即时调节电刺激，相比传统 DBS 可减少 40% 电能用量，改善 tremor 与肌肉僵硬，并支持算法切换以优化响应并降低副作用。', 'source': 'UCSF 公告 / Medical News', 'timestamp': '2025‑02'}, {'title': 'Onapgo 药物输注治疗 motor fluctuations', 'snippet': 'FDA 批准皮下输注 apomorphine，用于显著 “off” 时间的患者。', 'content': '2025 年 2 月 FDA 批准 Onapgo（apomorphine HCl）连续皮下注射输注疗法，适用于经历明显 motor fluctuations 或 off-time 的帕金森患者。输注系统可持续提供较稳定的血药浓度，迅速缓解 tremor 与运动迟缓，成为 levodopa 波动管理的重要补充治疗手段。', 'source': 'Michael J. Fox 基金会新闻', 'timestamp': '2025‑02‑04'}]}, {'db': 'search_document_db', 'result': [{'title': 'CuATSM 恢复 SOD1 功能：小鼠病症逆转研究', 'snippet': '在帕金森小鼠模型中，用 CuATSM 递送铜可防止神经退化，显著改善运动能力。', 'content': '研究由悉尼大学领导，27 只小鼠进行剂量探索后确立15\u202fmg/kg 为最佳剂量；之后对10 只帕金森样模型连续用药3 个月。治疗组运动能力保持稳定，多巴胺神经元在黑质得到保护，而对照组出现神经退化与运动恶化。CuATSM 恢复了 SOD1 抗氧化功能，预防自由基损伤，从而阻止疾病进展。', 'source': 'Wired 报道', 'timestamp': '2025‑07‑10'}, {'title': 'MLi‑2 抑制 LRRK2：促进神经纤毛再生与神经保护', 'snippet': 'MLi‑2 在 LRRK2 突变型小鼠中，再生纤毛，恢复细胞通信并提升神经保护。', 'content': '斯坦福团队对 LRRK2 高活性基因突变小鼠施用 MLi‑2，共持续3 个月；结果显示 striatum 中神经和神经胶质细胞的初级纤毛数量恢复至健康水平，神经信号传递增强，多巴胺突触密度翻倍，提示可能逆转病理性功能损害。', 'source': 'Wired 报道', 'timestamp': '2025‑07‑10'}, {'title': 'Tavapadon 新药：TEMPO\u202f3\u202f期临床数据', 'snippet': '腾博登（tavapadon）靶向 D1/D5 受体，延长“on time”，不良反应少。', 'content': 'TEMPO 3 试验结果显示，tavapadon 每日口服一次可延长患者的运动控制“on time”，且诱发幻觉、血压变化等不良事件明显少于传统 levodopa；该药可用于早期或与 levodopa 联用治疗中晚期患者，正在申请 FDA 批准阶段。', 'source': 'NY Post / AAN 大会报告', 'timestamp': '2025‑04‑18'}]}, {'db': 'search_personal_db', 'result': [{'title': '笔记：GLP‑1 类药物在帕金森中的神经保护潜力', 'snippet': '记录 lixisenatide 在临床中延缓症状的初步结果。', 'content': '2024 年法国 NS‑Park 网络试验中，156 名最近确诊患者接受 lixisenatide 治疗，组内 motor score 恶化比率显著低于安慰剂组，但部分有恶心、呕吐等副作用；结合 FT 报道指出 GLP‑1 激动剂（如 Mounjaro, Wegovy）正在扩展研究至帕金森对于神经炎症和神经保护的潜在作用。', 'created': '2025‑06‑30'}, {'title': '康复训练笔记：Rock Steady Boxing 对情绪与运动改善', 'snippet': '总结 RSB 对抑郁和运动症状的双重益处。', 'content': '依据 arXiv 2024 报告，40 名参与者接受为期 8 周每周两次的 Rock Steady Boxing，Beck 抑郁评分逐步下降，运动表现也有所改善；虽然有 6 人中途退出，但结果强调持续运动训练对改善非运动症状的效果。', 'created': '2025‑07‑15'}, {'title': '实验药 Solengepras（CVN‑424）阶段Ⅲ进展记录', 'snippet': 'GPR6 逆激动剂全口服小分子，进入 III 期临床。', 'content': 'Cerevance 开发的 Solengepras（CVN‑424）为 GPR6 逆激动剂，口服给药，2025 年初已进入 III 期试验阶段，动物模型显示能改善运动能力，未来可能作为 levodopa 替代或辅助疗法。', 'created': '2025‑05‑20'}]}]}, 'name': 'conversion_result', 'parts': [{'kind': 'text', 'text': '帕金森病的治疗方案主要包括以下几类：\n\n1. 药物治疗：\n- 左旋多巴（Levodopa）及其复合制剂，是最常用、最有效的药物。\n- 多巴胺受体激动剂（如普拉克索pramipexole、罗匹尼罗ropinirole、罗替戈汀rotigotine等）。\n- MAO-B抑制剂（如雷沙吉兰rasagiline、沙芬酰胺safinamide等）。\n- COMT抑制剂（如奥匹卡朋opicapone等）。\n- 其他药物：金刚烷胺（amantadine）、阿扑吗啡（apomorphine）等。\n- 新药进展：如tavapadon、Solengepras等新型药物正在临床试验阶段。\n\n2. 手术治疗：\n- 深部脑刺激（DBS），适用于药物控制不佳或出现运动并发症的患者。最新的自适应DBS（aDBS）可根据脑电信号自动调节刺激，副作用更低。\n\n3. 药物输注与新型给药方式：\n- 连续肠道Levodopa输注、皮下注射apomorphine等，用于运动波动明显的患者。\n\n4. 康复与非药物治疗：\n- 运动疗法（如Rock Steady Boxing等）、物理治疗、心理支持等。\n\n5. 新兴研究方向：\n- GLP-1受体激动剂（如lixisenatide、Mounjaro、Wegovy）在神经保护方面显示潜力。\n- 针对特定基因突变的靶向药物（如MLi-2）、抗氧化治疗（如CuATSM）等。\n\n帕金森病的治疗需个体化，具体方案应由神经科医生根据患者病情制定。如需了解某一类药物或手术的详细信息，可进一步提问。'}]}, 'contextId': '91754423-0369-4d8e-96b3-4cc65a6d0e2a', 'kind': 'artifact-update', 'taskId': '5cdc4260-1d21-4a64-ab9c-e43e9de7e74d'}}
2025/08/07 16:34:34
{'id': '93abcc32-62ae-48a6-ab70-8ee16d08912f', 'jsonrpc': '2.0', 'result': {'contextId': '91754423-0369-4d8e-96b3-4cc65a6d0e2a', 'final': True, 'kind': 'status-update', 'status': {'state': 'completed', 'timestamp': '2025-08-07T08:34:34.880328+00:00'}, 'taskId': '5cdc4260-1d21-4a64-ab9c-e43e9de7e74d'}}

```

# google 的A2A协议的taskId和contextId有啥区别
## taskId 与 contextId 的区别

* **taskId** 是每一个任务的唯一标识，是由服务器在工作流中生成（通常是 UUID）。它用于跟踪任务的整个执行流程，包括状态更新、消息交换、最终的结果 Artifact 等。换句话说，taskId 对应的是一个明确的「工作单」或「任务实例」。([Google Developer forums][1], [Cohorte][2])

* **contextId** 用于逻辑上将多个相关任务组织到同一个上下文或会话中。它通常也是由服务器生成，用于将一系列相关任务（或子任务）归类到一起，以便在复杂、多步骤或分布式的工作流中保持一致性和语境连续性。([Google][3], [Hugging Face][4])

---

### 比喻一下：

* 将 **taskId** 想象成一份具体的「工作单」号，用来追踪该任务从开始到完成的进度。
* 而 **contextId** 更像是一条「项目编号」，它可以串联起多个工作单(task)，让它们看起来属于同一个大项目或语境范畴。

---

## 应用场景

* 当你发起一个简单、一次性的请求（例如「帮我查一下今天的天气」），只需要一个 taskId 即可。
* 但在复杂场景中，例如：「帮我规划一个旅行行程」，这个任务可能会拆成子任务（查机票、查酒店、查景点等），这些子任务可以分别有唯一的 taskId，但通过同一个 contextId 关联起来，让系统知道它们都属于同一旅行计划。([Reddit][5], [Google Developer forums][1])

---

**总结**：

* **taskId**：每次交互的最小单位，唯一且专注于一个任务的执行。
* **contextId**：用于串联多个 task，形成一个上下文或会话背景，尤为适用于复杂或长流程的任务编排。
