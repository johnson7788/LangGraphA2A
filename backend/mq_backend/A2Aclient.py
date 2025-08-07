import logging
import time
import asyncio
from typing import Any
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendStreamingMessageRequest,
)

PUBLIC_AGENT_CARD_PATH = '/.well-known/agent.json'
EXTENDED_AGENT_CARD_PATH = '/agent/authenticatedExtendedCard'


class A2AClientWrapper:
    def __init__(self, session_id: str, task_id:str, agent_url: str):
        self.session_id = session_id
        self.task_id = task_id
        self.agent_url = agent_url
        self.logger = logging.getLogger(__name__)
        self.agent_card = None
        self.client: A2AClient | None = None

    async def _get_agent_card(self, resolver: A2ACardResolver) -> AgentCard:
        """
        获取 AgentCard（支持扩展卡优先，否则用 public 卡）
        """
        self.logger.info(f'尝试获取 Agent Card: {self.agent_url}{PUBLIC_AGENT_CARD_PATH}')
        public_card = await resolver.get_agent_card()
        self.logger.info('成功获取 public agent card:')
        self.logger.info(public_card.model_dump_json(indent=2, exclude_none=True))

        if public_card.supportsAuthenticatedExtendedCard:
            try:
                self.logger.info('支持扩展认证卡，尝试获取...')
                auth_headers_dict = {'Authorization': 'Bearer dummy-token-for-extended-card'}
                extended_card = await resolver.get_agent_card(
                    relative_card_path=EXTENDED_AGENT_CARD_PATH,
                    http_kwargs={'headers': auth_headers_dict},
                )
                self.logger.info('成功获取扩展认证 agent card:')
                self.logger.info(extended_card.model_dump_json(indent=2, exclude_none=True))
                return extended_card
            except Exception as e:
                self.logger.warning(f'获取扩展卡失败: {e}', exc_info=True)

        self.logger.info('使用 public agent card。')
        return public_card

    async def setup(self) -> None:
        async with httpx.AsyncClient(timeout=60.0) as httpx_client:
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=self.agent_url)
            try:
                agent_card = await self._get_agent_card(resolver)
                self.agent_card = agent_card
            except Exception as e:
                self.logger.error(f'获取 AgentCard 失败: {e}', exc_info=True)
                raise RuntimeError('无法获取 agent card，无法继续运行。') from e
    async def generate(self, user_question: str, history: list[dict]) -> None:
        """
        user_question: 用户问题
        history： 历史对话消息
        执行一次对话流程
        """
        if self.agent_card is None:
            await self.setup()
        logging.basicConfig(level=logging.INFO)
        async with httpx.AsyncClient(timeout=60.0) as httpx_client:
            self.client = A2AClient(httpx_client=httpx_client, agent_card=self.agent_card)
            self.logger.info('A2AClient 初始化完成。')

            # === 多轮对话 示例 ===
            self.logger.info("开始进行对话...")
            message_data: dict[str, Any] = {
                'message': {
                    'role': 'user',
                    'parts': [{'kind': 'text', 'text': user_question}],
                    'messageId': uuid4().hex,
                    'metadata': {'language': "English"},
                    'taskId': self.task_id,
                    'contextId': self.session_id,
                },
            }

            # === 流式响应 ===
            print("=== 流式响应开始 ===")
            streaming_request = SendStreamingMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(**message_data)
            )
            stream_response = self.client.send_message_streaming(streaming_request)

            async for chunk in stream_response:
                self.logger.info("=== 流式响应:  ===")
                print(chunk.model_dump(mode='json', exclude_none=True))

if __name__ == '__main__':
    async def main():
        session_id = time.strftime("%Y%m%d%H%M%S", time.localtime())
        wrapper = A2AClientWrapper(session_id=session_id, agent_url="http://localhost:10000")
        await wrapper.generate("帕金森的治疗方案有哪些?")
    asyncio.run(main())
