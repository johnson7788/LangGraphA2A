# 使用A2A协议的LangGraph货币代理

这个示例演示了一个使用[LangGraph](https://langchain-ai.github.io/langgraph/)构建并通过A2A协议暴露的货币转换代理。它展示了支持多轮对话和流式响应的会话交互。

## 工作原理

该代理使用LangGraph和LLM（例如Google Gemini）通过ReAct代理模式提供货币兑换信息。A2A协议实现了与代理的标准化交互，允许客户端发送请求并接收实时更新。

```mermaid
sequenceDiagram
    participant Client as A2A客户端
    participant Server as A2A服务器
    participant Agent as LangGraph代理
    participant API as Frankfurter API

    Client->>Server: 发送带有货币查询的任务
    Server->>Agent: 将查询转发给货币代理

    alt 信息完整
        Agent->>API: 调用get_exchange_rate工具
        API->>Agent: 返回汇率数据
        Agent->>Server: 处理数据并返回结果
        Server->>Client: 响应货币信息
    else 信息不完整
        Agent->>Server: 请求额外输入
        Server->>Client: 设置状态为"input-required"
        Client->>Server: 发送额外信息
        Server->>Agent: 转发额外信息
        Agent->>API: 调用get_exchange_rate工具
        API->>Agent: 返回汇率数据
        Agent->>Server: 处理数据并返回结果
        Server->>Client: 响应货币信息
    end

    alt 流式传输
        Note over Client,Server: 实时状态更新
        Server->>Client: "正在查找汇率..."
        Server->>Client: "正在处理汇率..."
        Server->>Client: 最终结果
    end
```


## 主要特性

- **多轮对话**：代理在需要时可以请求额外信息
- **实时流式传输**：在处理过程中提供状态更新
- **推送通知**：支持基于webhook的通知
- **会话记忆**：在交互中保持上下文
- **货币兑换工具**：与Frankfurter API集成以获取实时汇率

## 先决条件

- Python 3.12或更高版本
- 访问.env，配置 LLM和API密钥
- pip install -r requirements.txt


1. 运行代理：

   ```bash
   # 在自定义主机/端口上运行
   python main.py --host 0.0.0.0 --port 8080
   ```


2. 在单独的终端中运行测试客户端：

   ```bash
   python a2a_client.py
   ```


## 构建容器镜像

代理也可以使用容器文件构建。

1. 导航到`samples/python/agents/langgraph`目录：

  ```bash
  cd samples/python/agents/langgraph
  ```


2. 构建容器文件

    ```bash
    podman build . -t langgraph-a2a-server
    ```


> [!Tip]  
> Podman是`docker`的直接替代品，也可以在这些命令中使用。

3. 运行容器

    ```bash
    podman run -p 10000:10000 -e GOOGLE_API_KEY=your_api_key_here langgraph-a2a-server
    ```


4. 运行A2A客户端（按照上面第5步操作）

> [!Important]
> * **访问URL：** 您必须通过URL `0.0.0.0:10000` 访问A2A客户端。使用`localhost`将无法工作。
> * **主机名覆盖：** 如果您部署到容器外定义不同主机名的环境中，请使用`HOST_OVERRIDE`环境变量设置代理卡上的预期主机名。这确保与客户端应用程序的正确通信。

## 技术实现

- **LangGraph ReAct代理**：使用ReAct模式进行推理和工具使用
- **流式支持**：在处理过程中提供增量更新
- **检查点内存**：在回合之间保持对话状态
- **推送通知系统**：基于Webhook的更新与JWK认证
- **A2A协议集成**：完全符合A2A规范

## 限制

- 仅支持基于文本的输入/输出（无多模态支持）
- 使用Frankfurter API，货币选项有限
- 内存是基于会话的，服务器重启之间不会持久化

## 示例

**同步请求**

请求：

```
POST http://localhost:10000
Content-Type: application/json

{
    "id": "12113c25-b752-473f-977e-c9ad33cf4f56",
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
        "message": {
            "kind": "message",
            "messageId": "120ec73f93024993becf954d03a672bc",
            "parts": [
                {
                    "kind": "text",
                    "text": "10美元等于多少印度卢比？"
                }
            ],
            "role": "user"
        }
    }
}
```


响应：

```
{
    "id": "12113c25-b752-473f-977e-c9ad33cf4f56",
    "jsonrpc": "2.0",
    "result": {
        "artifacts": [
            {
                "artifactId": "08373241-a745-4abe-a78b-9ca60882bcc6",
                "name": "conversion_result",
                "parts": [
                    {
                        "kind": "text",
                        "text": "10美元等于856.2印度卢比。"
                    }
                ]
            }
        ],
        "contextId": "e329f200-eaf4-4ae9-a8ef-a33cf9485367",
        "history": [
            {
                "contextId": "e329f200-eaf4-4ae9-a8ef-a33cf9485367",
                "kind": "message",
                "messageId": "120ec73f93024993becf954d03a672bc",
                "parts": [
                    {
                        "kind": "text",
                        "text": "10美元等于多少印度卢比？"
                    }
                ],
                "role": "user",
                "taskId": "58124b63-dd3b-46b8-bf1d-1cc1aefd1c8f"
            },
            {
                "contextId": "e329f200-eaf4-4ae9-a8ef-a33cf9485367",
                "kind": "message",
                "messageId": "d8b4d7de-709f-40f7-ae0c-fd6ee398a2bf",
                "parts": [
                    {
                        "kind": "text",
                        "text": "正在查找汇率..."
                    }
                ],
                "role": "agent",
                "taskId": "58124b63-dd3b-46b8-bf1d-1cc1aefd1c8f"
            },
            {
                "contextId": "e329f200-eaf4-4ae9-a8ef-a33cf9485367",
                "kind": "message",
                "messageId": "ee0cb3b6-c3d6-4316-8d58-315c437a2a77",
                "parts": [
                    {
                        "kind": "text",
                        "text": "正在处理汇率..."
                    }
                ],
                "role": "agent",
                "taskId": "58124b63-dd3b-46b8-bf1d-1cc1aefd1c8f"
            }
        ],
        "id": "58124b63-dd3b-46b8-bf1d-1cc1aefd1c8f",
        "kind": "task",
        "status": {
            "state": "completed"
        }
    }
}
```


**多轮对话示例**

请求 - 第1步：

```
POST http://localhost:10000
Content-Type: application/json

{
    "id": "27be771b-708f-43b8-8366-968966d07ec0",
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
        "message": {
            "kind": "message",
            "messageId": "296eafc9233142bd98279e4055165f12",
            "parts": [
                {
                    "kind": "text",
                    "text": "1美元的汇率是多少？"
                }
            ],
            "role": "user"
        }
    }
}
```


响应 - 第2步：

```
{
    "id": "27be771b-708f-43b8-8366-968966d07ec0",
    "jsonrpc": "2.0",
    "result": {
        "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101",
        "history": [
            {
                "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101",
                "kind": "message",
                "messageId": "296eafc9233142bd98279e4055165f12",
                "parts": [
                    {
                        "kind": "text",
                        "text": "1美元的汇率是多少？"
                    }
                ],
                "role": "user",
                "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61"
            }
        ],
        "id": "9d94c2d4-06e4-40e1-876b-22f5a2666e61",
        "kind": "task",
        "status": {
            "message": {
                "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101",
                "kind": "message",
                "messageId": "f0f5f3ff-335c-4e77-9b4a-01ff3908e7be",
                "parts": [
                    {
                        "kind": "text",
                        "text": "请指定您想要转换成哪种货币。"
                    }
                ],
                "role": "agent",
                "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61"
            },
            "state": "input-required"
        }
    }
}
```


请求 - 第3步：

```
POST http://localhost:10000
Content-Type: application/json

{
    "id": "b88d818d-1192-42be-b4eb-3ee6b96a7e35",
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
        "message": {
            "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101",
            "kind": "message",
            "messageId": "70371e1f231f4597b65ccdf534930ca9",
            "parts": [
                {
                    "kind": "text",
                    "text": "加元"
                }
            ],
            "role": "user",
            "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61"
        }
    }
}
```


响应 - 第4步：

```
{
    "id": "b88d818d-1192-42be-b4eb-3ee6b96a7e35",
    "jsonrpc": "2.0",
    "result": {
        "artifacts": [
            {
                "artifactId": "08373241-a745-4abe-a78b-9ca60882bcc6",
                "name": "conversion_result",
                "parts": [
                    {
                        "kind": "text",
                        "text": "1美元兑换1.3739加元。"
                    }
                ]
            }
        ],
        "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101",
        "history": [
            {
                "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101",
                "kind": "message",
                "messageId": "296eafc9233142bd98279e4055165f12",
                "parts": [
                    {
                        "kind": "text",
                        "text": "1美元的汇率是多少？"
                    }
                ],
                "role": "user",
                "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61"
            },
            {
                "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101",
                "kind": "message",
                "messageId": "f0f5f3ff-335c-4e77-9b4a-01ff3908e7be",
                "parts": [
                    {
                        "kind": "text",
                        "text": "请指定您想要转换成哪种货币。"
                    }
                ],
                "role": "agent",
                "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61"
            },
            {
                "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101",
                "kind": "message",
                "messageId": "70371e1f231f4597b65ccdf534930ca9",
                "parts": [
                    {
                        "kind": "text",
                        "text": "加元"
                    }
                ],
                "role": "user",
                "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61"
            },
            {
                "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101",
                "kind": "message",
                "messageId": "0eb4f200-a8cd-4d34-94f8-4d223eb1b2c0",
                "parts": [
                    {
                        "kind": "text",
                        "text": "正在查找汇率..."
                    }
                ],
                "role": "agent",
                "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61"
            },
            {
                "contextId": "a7cc0bef-17b5-41fc-9379-40b99f46a101",
                "kind": "message",
                "messageId": "41c7c03a-a772-4dc8-a868-e8c7b7defc91",
                "parts": [
                    {
                        "kind": "text",
                        "text": "正在处理汇率..."
                    }
                ],
                "role": "agent",
                "taskId": "9d94c2d4-06e4-40e1-876b-22f5a2666e61"
            }
        ],
        "id": "9d94c2d4-06e4-40e1-876b-22f5a2666e61",
        "kind": "task",
        "status": {
            "state": "completed"
        }
    }
}
```


**流式传输示例**

请求：

```
{
    "id": "6d12d159-ec67-46e6-8d43-18480ce7f6ca",
    "jsonrpc": "2.0",
    "method": "message/stream",
    "params": {
        "message": {
            "kind": "message",
            "messageId": "2f9538ef0984471aa0d5179ce3c67a28",
            "parts": [
                {
                    "kind": "text",
                    "text": "10美元等于多少印度卢比？"
                }
            ],
            "role": "user"
        }
    }
}
```


响应：

```
data: {"id":"6d12d159-ec67-46e6-8d43-18480ce7f6ca","jsonrpc":"2.0","result":{"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","history":[{"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","kind":"message","messageId":"2f9538ef0984471aa0d5179ce3c67a28","parts":[{"kind":"text","text":"10美元等于多少印度卢比？"}],"role":"user","taskId":"423a2569-f272-4d75-a4d1-cdc6682188e5"}],"id":"423a2569-f272-4d75-a4d1-cdc6682188e5","kind":"task","status":{"state":"submitted"}}}

data: {"id":"6d12d159-ec67-46e6-8d43-18480ce7f6ca","jsonrpc":"2.0","result":{"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","final":false,"kind":"status-update","status":{"message":{"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","kind":"message","messageId":"1854a825-c64f-4f30-96f2-c8aa558b83f9","parts":[{"kind":"text","text":"正在查找汇率..."}],"role":"agent","taskId":"423a2569-f272-4d75-a4d1-cdc6682188e5"},"state":"working"},"taskId":"423a2569-f272-4d75-a4d1-cdc6682188e5"}}

data: {"id":"6d12d159-ec67-46e6-8d43-18480ce7f6ca","jsonrpc":"2.0","result":{"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","final":false,"kind":"status-update","status":{"message":{"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","kind":"message","messageId":"e72127a6-4830-4320-bf23-235ac79b9a13","parts":[{"kind":"text","text":"正在处理汇率..."}],"role":"agent","taskId":"423a2569-f272-4d75-a4d1-cdc6682188e5"},"state":"working"},"taskId":"423a2569-f272-4d75-a4d1-cdc6682188e5"}}

data: {"id":"6d12d159-ec67-46e6-8d43-18480ce7f6ca","jsonrpc":"2.0","result":{"artifact":{"artifactId":"08373241-a745-4abe-a78b-9ca60882bcc6","name":"conversion_result","parts":[{"kind":"text","text":"10美元等于856.2印度卢比。"}]},"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","kind":"artifact-update","taskId":"423a2569-f272-4d75-a4d1-cdc6682188e5"}}

data: {"id":"6d12d159-ec67-46e6-8d43-18480ce7f6ca","jsonrpc":"2.0","result":{"contextId":"cd09e369-340a-4563-bca4-e5f2e0b9ff81","final":true,"kind":"status-update","status":{"state":"completed"},"taskId":"423a2569-f272-4d75-a4d1-cdc6682188e5"}}
```


## 了解更多

- [A2A协议文档](https://a2aproject.github.io/A2A/)
- [LangGraph文档](https://langchain-ai.github.io/langgraph/)
- [Frankfurter API](https://www.frankfurter.app/docs/)
- [Google Gemini API](https://ai.google.dev/gemini-api)


## 免责声明
重要提示：提供的示例代码仅供演示目的，说明了Agent-to-Agent（A2A）协议的机制。在构建生产应用程序时，必须将任何在您直接控制之外运行的代理视为潜在的不受信任实体。

来自外部代理的所有数据——包括但不限于其AgentCard、消息、工件和任务状态——都应作为不受信任的输入处理。例如，恶意代理可能在其字段中提供包含精心制作数据的AgentCard（例如，描述、名称、skills.description）。如果在未进行清理的情况下使用这些数据来构建大型语言模型（LLM）的提示，可能会使您的应用程序遭受提示注入攻击。未能在使用前正确验证和清理这些数据可能会在您的应用程序中引入安全漏洞。

开发人员有责任实施适当的安全措施，如输入验证和安全处理凭证，以保护其系统和用户。