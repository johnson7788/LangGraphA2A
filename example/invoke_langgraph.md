human: 你好啊，介绍下什么是LangGraph
ai: [{'name': 'web_search', 'args': {'query': '什么是LangGraph'}, 'id': 'call_BrblgSpqSxqfRFUAiDYzqixA', 'type': 'tool_call'}]
tool: LangGraph核心技术概念，LangGraph和LangChain同宗同源，底层架构完全相同、接口完全相通。从开发者角度来说，LangGraph也是使用LangChain底层API来接入各类大模型、LangGraph也完全兼容LangChain内置的一系列工具。换而言之，LangGraph的核心功能都是依托LangChain来完成。但是和LangChain的链式工作流哲学完全不同的是，LangGraph的基础哲学是构建图结构的工作流，并引入“状态”这一核心概念来描绘任务执行情况，从而拓展了LangChain LCEL链式语法的功能灵活程度。
ai: LangGraph是一种基于图结构的工作流框架，和LangChain同宗同源，底层架构和接口完全兼容。它主要用于构建和管理大模型（如GPT等）驱动的复杂任务流程。

与LangChain的“链式”工作流不同，LangGraph的核心理念是“图结构”工作流，并引入了“状态”这一核心概念，用于描述和追踪任务的执行情况。这种设计让LangGraph在处理复杂、多分支、多状态的AI任务时更加灵活和强大。

简而言之，LangGraph是一个基于LangChain底层API、专注于图结构和状态管理的AI工作流框架，适合需要高度自定义和复杂流程控制的场景。