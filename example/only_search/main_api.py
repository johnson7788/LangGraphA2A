# main.py
import logging
import os
from dotenv import load_dotenv
load_dotenv()

logfile = os.path.join("api.log")
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s -  %(message)s',
    datefmt='%Y/%m/%d %H:%M:%S',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(logfile, mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

import click
# 这里不再从这里直接运行 uvicorn；仅在 __main__ 时使用
# import uvicorn

from adk_agent_executor import ADKAgentExecutor
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from starlette.routing import Route
from google.adk.agents.run_config import RunConfig, StreamingMode
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from starlette.middleware.cors import CORSMiddleware
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from slide_agent.agent import root_agent

def build_app(agent_url: str | None = None):
    # 运行模式（默认非流式，避免结构化输出被打断）
    streaming = False
    show_agent = ["SummaryAgent"]

    agent_card_name = "Search Agent"
    agent_name = "search_agent"
    agent_description = "搜索"

    skill = AgentSkill(
        id=agent_name,
        name=agent_name,
        description=agent_description,
        tags=["search"],
        examples=["search"],
    )

    # 允许通过环境变量覆盖对外地址
    env_agent_url = os.getenv("AGENT_URL", "").strip()
    if not agent_url:
        agent_url = env_agent_url or "http://localhost:10039/"
    print(f"AGENT_URL的地址为：{agent_url}")

    agent_card = AgentCard(
        name=agent_card_name,
        description=agent_description,
        url=agent_url,
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )

    runner = Runner(
        app_name=agent_card.name,
        agent=root_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )

    if streaming:
        logger.info("使用 SSE 流式输出模式")
        run_config = RunConfig(streaming_mode=StreamingMode.SSE, max_llm_calls=500)
    else:
        logger.info("使用普通输出模式")
        run_config = RunConfig(streaming_mode=StreamingMode.NONE, max_llm_calls=500)

    agent_executor = ADKAgentExecutor(runner, agent_card, run_config, show_agent)
    request_handler = DefaultRequestHandler(agent_executor=agent_executor, task_store=InMemoryTaskStore())
    a2a_app = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)
    app = a2a_app.build()

    # CORS
    from starlette.middleware.cors import CORSMiddleware as _C
    app.add_middleware(
        _C,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app

app = build_app()

@click.command()
@click.option("--host", "host", default="localhost", help="服务器绑定的主机名（默认为 localhost,可以指定具体本机ip）")
@click.option("--port", "port", default=10039, help="服务器监听的端口号（默认为 10039）")
@click.option("--agent_url", "agent_url", default="", help="Agent Card中对外展示和访问的地址")
def main(host, port, agent_url=""):
    # 本地开发模式下仍可直接运行：python main.py --host 0.0.0.0 --port 10039
    import uvicorn
    if not agent_url:
        agent_url = os.getenv("AGENT_URL", "").strip()
    if not agent_url:
        agent_url = f"http://{host}:{port}/"
    # 临时用指定的 agent_url 重新构建 app
    local_app = build_app(agent_url=agent_url)
    logger.info(f"服务启动中，监听地址: http://{host}:{port}")
    uvicorn.run(local_app, host=host, port=port)

if __name__ == "__main__":
    main()
