import logging
from typing import Any
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)

PUBLIC_AGENT_CARD_PATH = '/.well-known/agent.json'
EXTENDED_AGENT_CARD_PATH = '/agent/authenticatedExtendedCard'

async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    base_url = 'http://localhost:10000'

    async with httpx.AsyncClient(timeout=30.0) as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        final_agent_card_to_use: AgentCard | None = None

        try:
            logger.info(f'尝试获取 Agent Card: {base_url}{PUBLIC_AGENT_CARD_PATH}')
            _public_card = await resolver.get_agent_card()
            logger.info('成功获取 public agent card:')
            logger.info(_public_card.model_dump_json(indent=2, exclude_none=True))
            final_agent_card_to_use = _public_card

            if _public_card.supportsAuthenticatedExtendedCard:
                try:
                    logger.info('支持扩展认证卡，尝试获取...')
                    auth_headers_dict = {'Authorization': 'Bearer dummy-token-for-extended-card'}
                    _extended_card = await resolver.get_agent_card(
                        relative_card_path=EXTENDED_AGENT_CARD_PATH,
                        http_kwargs={'headers': auth_headers_dict},
                    )
                    logger.info('成功获取扩展认证 agent card:')
                    logger.info(_extended_card.model_dump_json(indent=2, exclude_none=True))
                    final_agent_card_to_use = _extended_card
                except Exception as e_extended:
                    logger.warning(f'获取扩展卡失败: {e_extended}', exc_info=True)
            else:
                logger.info('Agent 不支持扩展认证卡，使用 public card。')

        except Exception as e:
            logger.error(f'获取 AgentCard 失败: {e}', exc_info=True)
            raise RuntimeError('无法获取 agent card，无法继续运行。') from e

        client = A2AClient(httpx_client=httpx_client, agent_card=final_agent_card_to_use)
        logger.info('A2AClient 初始化完成。')

        # === 单轮对话 ===
        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [{'kind': 'text', 'text': '帕金森的治疗方案有哪些？'}],
                'messageId': uuid4().hex,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**send_message_payload)
        )

        response = await client.send_message(request)
        print("=== 单轮问答响应 ===")
        print(response.model_dump(mode='json', exclude_none=True))

        # === 多轮对话 ===
        logger.info("开始进行多轮对话...")

        multiturn_first: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [{'kind': 'text', 'text': '帕金森的治疗方案有哪些？'}],
                'messageId': uuid4().hex,
            },
        }
        multiturn_req1 = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**multiturn_first),
        )
        resp1 = await client.send_message(multiturn_req1)
        print("=== 多轮对话 - 第一步响应 ===")
        print(resp1.model_dump(mode='json', exclude_none=True))

        task_id = resp1.root.result.id
        contextId = resp1.root.result.contextId

        multiturn_second: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [{'kind': 'text', 'text': '有没有什么推荐的预防手段？'}],
                'messageId': uuid4().hex,
                'taskId': task_id,
                'contextId': contextId,
            },
        }
        multiturn_req2 = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**multiturn_second),
        )
        resp2 = await client.send_message(multiturn_req2)
        print("=== 多轮对话 - 第二步响应 ===")
        print(resp2.model_dump(mode='json', exclude_none=True))

        # === 流式对话 ===
        print("=== 流式响应 示例 ===")
        streaming_request = SendStreamingMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**send_message_payload)
        )
        stream_response = client.send_message_streaming(streaming_request)

        async for chunk in stream_response:
            print(chunk.model_dump(mode='json', exclude_none=True))


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
