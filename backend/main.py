import logging
import os
import sys
import click
import httpx
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from dotenv import load_dotenv
from agent_executor import KnowledgeAgentExecutor  # 引入新的知识库 Agent

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10000)
def main(host, port):
    """启动知识库问答 Agent 服务。"""
    try:
        capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
        skill = AgentSkill(
            id='knowledge_search',
            name='知识库问答能力',
            description='可以从文档、个人知识库和指南中检索信息并回答用户问题',
            tags=['知识检索', '多轮问答', '智能助手'],
            examples=['帕金森的治疗方案有哪些？', '我在指南中能找到哪些营养建议？'],
        )

        agent_card = AgentCard(
            name='知识库问答 Agent',
            description='可以根据用户的问题从多个知识库中检索并回答',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=KnowledgeAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=KnowledgeAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        # 启动服务
        httpx_client = httpx.AsyncClient()
        request_handler = DefaultRequestHandler(
            agent_executor=KnowledgeAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_notifier=InMemoryPushNotifier(httpx_client),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler
        )

        uvicorn.run(server.build(), host=host, port=port)

    except Exception as e:
        logger.error(f'启动 Agent 服务出错: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
