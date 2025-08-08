# 实现思路

# 后端
## 知识库后端
[knowledge_agent](knowledge_agent)

## Rabbit MQ后端（负责读取MQ消息，创建Agent，然后发送结果给MQ不同的channel)
[mq_backend](mq_backend)

## 和前端进行交互(使用fastapi撰写， 负责写消息到Rabbit MQ)
[api_gateway](api_gateway)