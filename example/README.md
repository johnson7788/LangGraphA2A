# 文件解释

## 带Thingking的模型，流式输出
[think_stream_langgraph.py](think_stream_langgraph.py)

## 流式输出
[stream_langgraph.py](stream_langgraph.py)
[stream_langgraph.md](stream_langgraph.md)

## values模式
[stream_values_langgraph.py](stream_values_langgraph.py)

## 工具非流式输出，其它流式输出
[stream_langgraph_tool_nostream.py](stream_langgraph_tool_nostream.py)
[stream_langgraph_tool_nostream.md](stream_langgraph_tool_nostream.md)

## 多轮对话能力，通过传入history实现
[history_langgraph.py](history_langgraph.py)

## 工具的获取记忆的state和更新记忆state
[inject_command_tool.py](inject_command_tool.py)

## 多个工具更新同一个记忆state的key
[inject_command_update.py](inject_command_update.py)

## 模拟搜索
[search.py](search.py)

## 使用tool工具进行计划设定
[plan_langgraph.py](plan_langgraph.py)

## MCP工具(streamable-http协议)
[mcp_search.py](mcp_search.py)

## langgraph使用mcp
[mcp_langgraph.py](mcp_langgraph.py)

## 加载本地的mcp_config.json
[mcp_load_config_langgraph.py](mcp_load_config_langgraph.py)

## 由开发者注入的参数（不经过 LLM)，即LLM不可见工具的部分参数
[invoke_inject_tool_arg.py](invoke_inject_tool_arg.py)