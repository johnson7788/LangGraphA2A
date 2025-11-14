import json
import uuid
import httpx
import time
from a2a.client import A2AClient
import asyncio
from a2a.types import (MessageSendParams, SendStreamingMessageRequest)

async def httpx_client():
    timeout = httpx.Timeout(30.0)
    async with httpx.AsyncClient(timeout=timeout) as httpx_client:
        client = await A2AClient.get_client_from_agent_card_url(
            httpx_client, 'http://localhost:10039'
        )
        request_id = uuid.uuid4().hex
        send_message_payload = {
            'message': {
                'role': 'user',
                'parts': [{'type': 'text', 'text': prompt}],
                'messageId': request_id
            },
            # 关键：通过 metadata 指定需要的创新点个数
            'metadata': metadata
        }
        print(f"发送message信息: {send_message_payload}")
        streaming_request = SendStreamingMessageRequest(
            id=request_id,
            params=MessageSendParams(**send_message_payload)
        )
        stream_response = client.send_message_streaming(streaming_request)
        async for chunk in stream_response:
            print(time.time())
            print(chunk.model_dump(mode='json', exclude_none=True))
            chunk_json = chunk.model_dump(mode='json', exclude_none=True)
            print(chunk_json)

if __name__ == '__main__':
    # 示例输入
    prompt = """我是一名胸科医院的医生，在工作中发现，结核病患者肺癌的发生率较普通人群明显升高。进一步文献调研，发现国内外众多队列研究和荟萃分析均证实，肺结核是肺癌发生的独立危险因素，具有肺结核病史者罹患肺癌的风险是普通人群的2.17倍。如果我想进行一些肺结核如何增加肺癌发生的分子机制创新性研究，可以聚焦在哪些方面呢？"""
    metadata = {"num_innovations": 2}
    asyncio.run(httpx_client())
