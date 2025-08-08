# 和前端进行交互的后端

## ✦ 代码说明

1. `main.py`:
    * FastAPI应用: 创建一个FastAPI实例。
    * RabbitMQ连接: 从环境变量中读取配置信息。
    * `/chat` 端点:
        * 接收POST请求，请求体格式应为 {"userId": "...", "messages": [...]}。
        * 生成一个唯一的 sessionId。
        * 将消息进行双重JSON编码，然后发布到 QUEUE_NAME_QUESTION 队列。
        * 返回一个 EventSourceResponse，这是一个SSE响应，会保持连接打开。
    * SSE事件生成器 (`event_generator`):
        * 为每个请求创建一个唯一的 asyncio.Queue，并用 sessionId 作为键存储在全局的 sse_queues 字典中。
        * 异步地等待从队列中获取消息。
        * 每当从队列中获取到一条消息，就将其作为SSE事件发送给前端。
        * 当收到 [stop] 消息时，发送一个 end 事件并关闭连接。
    * RabbitMQ监听器 (`listen_to_answer_queue`):
        * 在后台线程中运行，持续监听 QUEUE_NAME_ANSWER 队列。
        * 当收到消息时，它会根据消息中的 sessionId 找到对应的SSE队列，并将消息放入该队列。
        * 这样，event_generator 就能获取到消息并发送给前端。

## 如何运行

1. 安装依赖:

   1     pip install -r /Users/admin/git/LangGraphA2A/backend/api_gateway/requirements.txt



2. 配置环境变量:
   复制 env_template 文件为 .env，并根据您的实际情况修改其中的值。


   1     cp /Users/admin/git/LangGraphA2A/backend/api_gateway/env_template
     /Users/admin/git/LangGraphA2A/backend/api_gateway/.env


3. 启动应用:

   1     uvicorn api_gateway.main:app --host 0.0.0.0 --port 8000 --reload

      或者直接运行


   1     python /Users/admin/git/LangGraphA2A/backend/api_gateway/main.py


## 如何测试
您可以使用 curl 或任何API客户端来测试。

发送请求:
```bash
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{
  "userId": "test_user",
  "messages": [
    {"role": "user", "content": "帕金森的治疗方案有哪些?"}
  ]
}'
```

