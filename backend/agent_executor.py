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
                is_task_complete = item['is_task_complete']
                require_user_input = item['require_user_input']
                # 自己组织的返回给前端的元数据
                metadata = item['metadata']

                if not is_task_complete and not require_user_input:
                    await updater.update_status(
                        TaskState.working,
                        updater.new_agent_message(
                            parts = item['content'],
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


def convert_genai_parts_to_a2a(parts: list[Part]) -> list[Part]:
    """提取Event的结果信息，函数的call和response等信息, AI结果转成Part"""
    return [
        convert_genai_part_to_a2a(part)
        for part in parts
        if (part.text or part.file_data or part.inline_data or part.function_call or part.function_response)
    ]


def convert_genai_part_to_a2a(part: Part) -> Part:
    """Convert a single Google Gen AI Part type into an A2A Part type."""
    if part.text:
        return TextPart(text=part.text)
    if part.file_data:
        return FilePart(
            file=FileWithUri(
                uri=part.file_data.file_uri,
                mime_type=part.file_data.mime_type,
            )
        )
    if part.inline_data:
        return Part(
            root=FilePart(
                file=FileWithBytes(
                    bytes=part.inline_data.data,
                    mime_type=part.inline_data.mime_type,
                )
            )
        )
    if part.function_call:
        # print(f"function_call , {part}")
        function_data = extract_function_info_to_datapart(part)
        return DataPart(data=function_data)
    if part.function_response:
        # print(f"function_response, {part}")
        function_data = extract_function_info_to_datapart(part)
        return DataPart(data=function_data)
    raise ValueError(f"Unsupported part type: {part}")


def extract_function_info_to_datapart(part: Part) -> DataPart:
    """
    从一系列Part对象中提取function_call或function_response信息，
    并将其封装为DataPart对象。

    Args:
        part: 包含Part对象
    Returns:
        DataPart对象。
    """
    extracted_data = {}

    if part.function_call:
        # 提取 function_call 信息
        extracted_data = {
            "type": "function_call",
            "id": part.function_call.id,
            "name": part.function_call.name,
            "args": part.function_call.args
        }
    elif part.function_response:
        # 提取 function_response 信息
        extracted_data = {
            "type": "function_response",
            "id": part.function_response.id,
            "name": part.function_response.name,
            "response": part.function_response.response
        }
    return extracted_data