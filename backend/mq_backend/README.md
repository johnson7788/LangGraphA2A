# RabbitMQ后端
并发，调用Agent返回结果

# 创建容器
```
docker run -d --hostname rabbitapp --name rabbitapp -e RABBITMQ_DEFAULT_USER=admin -e RABBITMQ_DEFAULT_PASS=welcome -p 4369:4369 -p 5671:5671 -p 5672:5672 -p 25672:25672 -p 15671:15671 -p 15672:15672 -p 15691:15691 -p 15692:15692 rabbitmq:3-management
```

核心交互流程


   1. 发送端 (`api_gateway`): 将用户的请求打包成一个特定格式的JSON消息，发送到名为 QUEUE_NAME_QUESTION 的RabbitMQ队列。
   2. 处理端 (`mq_backend`):
       * 监听 QUEUE_NAME_QUESTION 队列。
       * 接收到消息后，解析内容，并调用 knowledge_agent。
       * 将 knowledge_agent 返回的流式响应，分块、格式化后，发送到名为 QUEUE_NAME_ANSWER 的队列。
   3. 接收端 (可以是 `api_gateway` 或其他服务): 监听 QUEUE_NAME_ANSWER
      队列，接收处理结果并推送给前端（例如，通过WebSocket）。

  ---

  如何使用 mq_backend

  1. 环境配置


  您的 api_gateway 应用需要访问和 mq_backend 相同的环境变量来连接到RabbitMQ。请确保以下变量已配置：



   1 RABBITMQ_HOST=...
   2 RABBITMQ_PORT=...
   3 RABBITMQ_USERNAME=...
   4 RABBITMQ_PASSWORD=...
   5 RABBITMQ_VIRTUAL_HOST=...
   6 QUEUE_NAME_QUESTION=... # 用于发送任务的队列名
   7 QUEUE_NAME_ANSWER=...   # 用于接收结果的队列名


  2. 发送任务到 mq_backend


  要触发 mq_backend 中的处理流程，您需要向 QUEUE_NAME_QUESTION 发送一条消息。

  关键点：


   * 队列名称: QUEUE_NAME_QUESTION
   * 消息格式: 一个双重序列化的JSON字符串。这是根据 main_api.py 和 test_api.py
     的实现得出的一个关键细节。您需要先将一个Python字典序列化为JSON字符串，然后再将这个字符串再次序列化。

  消息体结构 (内层JSON):

    1 {
    2   "sessionId": "string",    // 必选：唯一标识一次会话，用于保持上下文
    3   "userId": "string",       // 必选：用户标识
    4   "functionId": 8,          // 必选：功能ID，目前固定为 8，代表调用Agent RAG问答
    5   "messages": [             // 必选：一个消息列表，包含历史记录和当前问题
    6     {
    7       "role": "user",
    8       "content": "我叫Johnson Guo"
    9     },
   10     {
   11       "role": "ai",
   12       "content": "很高兴认识你"
   13     },
   14     {
   15       "role": "user",
   16       "content": "你知道我叫什么吗?" // 当前问题总是在列表的最后一个
   17     }
   18   ]
   19 }
   

  不同 `type` 的含义:

   * type: 4 (文本或停止信号)
       * 如果 message 是一个字符串，代表是LLM生成的回答文本块。
       * 如果 message 是 '[stop]'，代表流式响应结束。
       * 如果 reasoningMessage 有内容，代表是Agent的思考过程。
   * type: 5 (工具数据)
       * message 字段是一个JSON字符串，包含了工具调用返回的数据，用于在前端展示。
   * type: 6 (引用和参考)
       * message 字段是一个JSON字符串，包含了从知识库中检索到的原始数据或引用来源。
   * type: 7 (实体)
     * message 字段是一个JSON字符串，包含了实体识别的结果。