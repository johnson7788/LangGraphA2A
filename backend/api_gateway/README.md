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

# 多用户的原理
  整个系统通过 sessionId 这个关键标识符来确保每个用户的数据流向正确的客户端。

   1. 会话开始 (api_gateway/main.py)
       * 当一个新用户通过浏览器发起 /chat 请求时，api_gateway 的 chat_endpoint 函数会立即为这次会话创建一个全局唯一的 session_id
         (session_id = str(uuid4()))。
       * 这个 session_id 会被打包进要发送给后端的 RabbitMQ 消息中。

   2. 任务分发 (api_gateway -> RabbitMQ -> mq_backend)
       * api_gateway 将带有 session_id 的消息发布到 question_queue。
       * mq_backend/main_api.py 从 question_queue 中消费这条消息。它内部有一个线程池
         (ThreadPoolExecutor)，可以并发处理多个用户的请求。

   3. 任务处理与响应 (mq_backend -> RabbitMQ)
       * mq_backend 在处理完请求后（例如，调用大模型），会将响应数据（无论是最终结果还是流式数据块）原封不动地附上原始的
         `session_id`，然后发送回 answer_queue。
       * 这一点至关重要：mq_backend 并不关心这个 session_id 对应哪个具体的用户连接，它只是一个任务处理者，忠实地处理任务并用
         session_id 标记好“回信”的收件人。

   4. 响应路由与投递 (api_gateway)
       * 这是解决你疑虑的核心部分。api_gateway 中有一个全局的、线程安全的字典 sse_queues = {}。
       * 当为用户创建 SSE (Server-Sent Events) 连接时，它会以 session_id 为键 (key)，创建一个专属的 asyncio.Queue 作为值
         (value)，并存入 sse_queues 字典中。sse_queues 的结构看起来像这样：
   1         {
   2             "session_id_for_user_A": <Queue object for User A>,
   3             "session_id_for_user_B": <Queue object for User B>,
   4             ...
   5         }
       * api_gateway 中有一个后台监听线程 (listen_to_answer_queue)，它唯一的工作就是从 answer_queue 中取出所有消息。
       * 每当监听到一条消息，它会解析消息内容，提取出 session_id。
       * 然后，它会用这个 session_id 作为 key 在 sse_queues 字典里查找对应的用户队列，并将消息放入该队列
         (sse_queues[session_id].put_nowait(message))。

  总结

   - 隔离性：通过为每个聊天会话生成唯一的 session_id，并将用户的 SSE 连接与这个 ID
     绑定，系统确保了不同用户之间的通信是完全隔离的。
   - 无状态后端：mq_backend 是无状态的，它不需要管理用户连接，只需处理带有 session_id 的任务单元，这使得 mq_backend
     很容易横向扩展（即启动更多的实例来处理更多请求）。
   - 有状态网关：api_gateway 是有状态的，它通过 sse_queues 字典维护了所有活动的用户连接状态。它像一个路由器或分发中心，确保从
     answer_queue 过来的每一条消息都能准确无误地投递给正确的用户。

  所以，即使成百上千的用户同时使用，api_gateway 也能根据每条消息的
  session_id，精确地将它路由到正确的客户端，不会发生数据混乱的情况。这个设计是健壮且可扩展的