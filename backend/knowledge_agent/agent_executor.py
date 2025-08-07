import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    Task,
    UnsupportedOperationError,
    AgentCard,
    Artifact,
    FilePart,
    FileWithBytes,
    FileWithUri,
    GetTaskRequest,
    GetTaskSuccessResponse,
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    SendMessageSuccessResponse,
    TaskQueryParams,
    TaskState,
    TaskStatus,
    TextPart,
    DataPart,
)

from a2a.utils import (
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError

from agent import KnowledgeAgent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeAgentExecutor(AgentExecutor):
    """知识问答 AgentExecutor 示例."""

    def __init__(self):
        self.agent = KnowledgeAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        error = self._validate_request(context)
        if error:
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        metadata = context.message.metadata
        print(f"收到用户的问题: {query}, 传入的metadata信息是: {metadata}")
        print(f"Context ID: {context.context_id}, Task ID: {context.task_id}")
        task = context.current_task
        if not task:
            task = new_task(context.message) # type: ignore
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.contextId)
        try:
            async for item in self.agent.stream(query, task.contextId):
                print(f"Agent返回的数据信息: {item}")
                is_task_complete = item['is_task_complete']
                require_user_input = item['require_user_input']
                # 自己组织的返回给前端的元数据
                metadata = item['metadata']

                if not is_task_complete and not require_user_input:
                    await updater.update_status(
                        TaskState.working,
                        updater.new_agent_message(
                            parts = convert_genai_parts_to_a2a(item),
                            metadata = metadata
                        ),
                    )
                elif require_user_input:
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(
                            item['content'],
                            task.contextId,
                            task.id,
                        ),
                        final=True,
                    )
                    break
                else:
                    await updater.add_artifact(
                        [Part(root=TextPart(text=item['content']))],
                        name='conversion_result',
                        metadata=metadata
                    )
                    await updater.complete()
                    break

        except Exception as e:
            logger.error(f'An error occurred while streaming the response: {e}')
            raise ServerError(error=InternalError()) from e

    def _validate_request(self, context: RequestContext) -> bool:
        return False

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise ServerError(error=UnsupportedOperationError())


def convert_genai_parts_to_a2a(item: dict) -> list[Part]:
    """提取Event的结果信息，函数的call和response等信息, AI结果转成Part, 对Agent的Stream进行解析"""
    data_type = item.get("data_type", "unknown")
    content = item.get("content")
    if data_type == "result":
        return [TextPart(text=content)]
    elif data_type == "error":
        return [TextPart(text=content)]
    elif data_type == "require_user":
        return [TextPart(text=content)]
    elif data_type == "tool_call":
        return [DataPart(data={"data": item["data"]})]
    elif data_type == "tool_response":
        return [DataPart(data=item["data"])]
    raise ValueError(f"未知的stream返回的数据类型，请检查stream函数: {data_type}")