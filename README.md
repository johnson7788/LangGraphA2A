# 单Agent的Agent RAG问答，结合MCP

## 🚀 简介

基于 **LangGraph** 和 **Google A2A 协议** 构建的智能 Agent 系统，支持 React 前端与 Python 后端协同工作。用户可以通过多轮对话与系统交互，系统实时展示“思考过程”、关联实体并查询数据库，同时在回答中附带来源标签并支持流式输出。

---

## 功能特性

1. **多数据源切换**
   支持用户选择不同数据源（如：数据库、知识库等），后端根据源动态调用。

2. **思考过程展示**
   后端使用 LangGraph 的 ReAct 模式，卡片形式逐步展示 agent 的推理链条。

3. **回答中实体关联数据库查询**
   系统识别回答中的实体（Entity），向数据库发起关联查询并将结果整合进最终答案。

4. **回答结果带参考来源标签**
   每次输出的答案中会标注引用来源，例如 `[来源]`。

5. **回答数据流中包含参考来源**
   在 Agent 的内部执行流／SSE 流式输出中，也传递每一步来源信息，用于前端展示。

6. **多轮对话支持**
   支持会话上下文管理，多轮交互保持记忆和上下文链。

7. **流式输出**
   支持 A2A 的订阅式任务，客户端通过 SSE 接收 incremental 输出来刷新界面。

8. ** MCP **
    即插即用MCP

---

## 📂 项目结构

```

```

---

## ⚙️ 技术栈

* **后端（Python）**

  * LangGraph + LangChain 创建 ReAct agent（支持工具调用 & 思考过程建模）
  * Google A2A Python SDK（实现 `send` 和 `sendSubscribe` 接口）
  * 多数据源适配器设计，自定义 `data_sources.py` 统一调用接口
  * 实体识别与数据库查询模块（entity_linker）
  * SSE 流式任务更新：通过 `enqueue_events_for_sse` 等方法推送思考／来源信息

* **前端（React）**

  * 支持多数据源选择 UI
  * 会话展示组件：展示用户提问、Agent 思考（链式过程）和最终答案
  * 实时更新显示：以 SSE 接收服务端中间流程并及时渲染
  * 引用来源标签 UI：展示每段内容（思考或答案）对应的来源标签

---

## 🧪 使用示例

### 后端启动

```bash
cd backend

```

### 前端启动

```bash
cd frontend
npm install
npm run start
```

### 交互流程

1. 用户选择某个数据源，输入问题
2. 前端调用后端 A2A agent 接口
3. 后端逐步推理，调用数据查询工具、实体关联、构建 user-agent-output 等每一步通过 SSE 返回
4. 前端不断渲染：

   * 思考内容 + 来源标签
   * 最终答案 + 实体查询内容和来源标识
5. 用户可继续输入下一轮问题，系统保持上下文，多轮对话继续

---

## 🎯 设计亮点

* **来源透明**：每一步逻辑与查询都带来源元标签，无论最终答案还是中间推理都可追踪
* **流式交互**：支持 SSE 将 agent 思考过程同步给前端，提升用户体验
* **模块化设计**：后端清晰拆分数据源适配器、实体识别、A2A Task 管理、LangGraph Agent 逻辑
* **多轮记忆**：LangGraph + A2A 保持上下文状态，支持连续对话

---

## UI界面
![Home1.png](doc%2FHome1.png)
![Home2.png](doc%2FHome2.png)


## todo:
* tool metadata ✅
* metadata返回 ✅
* Step Streaming 返回，LLM的每一个步骤返回给client ✅
* LLM Token Streaming 返回 ✅
* MCP 外挂集成 ✅
* 工具动态切换，根据传入的tool的metadata，使用不同的工具（根据tool不同，创建不同的graph)
* LLM Thinking 返回
* Plan 模式 
* 改造 https://github.com/google-gemini/gemini-fullstack-langgraph-quickstart  也为A2A形式

## 🤝Wechat
![weichat.png](doc%2Fweichat.png)
