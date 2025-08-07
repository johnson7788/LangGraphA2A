# RabbitMQ后端
并发，调用Agent返回结果

# 创建容器
```
docker run -d --hostname rabbitapp --name rabbitapp -e RABBITMQ_DEFAULT_USER=admin -e RABBITMQ_DEFAULT_PASS=welcome -p 4369:4369 -p 5671:5671 -p 5672:5672 -p 25672:25672 -p 15671:15671 -p 15672:15672 -p 15691:15691 -p 15692:15692 rabbitmq:3-management
```