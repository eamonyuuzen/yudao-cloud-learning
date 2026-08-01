import asyncio

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    RunConfig,
    Runner,
)
from agents.run_config import ToolExecutionConfig
from openai import AsyncOpenAI

from internship_task_agent.config import Settings, get_settings
from internship_task_agent.context import AgentRequestContext
from internship_task_agent.schemas import AgentQueryResponse
from internship_task_agent.tools import query_internship_tasks
from internship_task_agent.trace import TraceCollector
from internship_task_agent.yudao_client import YudaoClient

INSTRUCTIONS = """
你是实习任务只读查询助手。

规则：
1. 只有用户明确询问实习任务时，才调用 query_internship_tasks。
2. 不得新增、修改、删除或切换任务状态。
3. 不得编造工具结果中不存在的任务。
4. ok=false 时保留错误语义：
   UNAUTHENTICATED 提示重新登录；
   FORBIDDEN 明确说明没有权限；
   BACKEND_UNAVAILABLE 说明服务暂时不可用；
   TOOL_LIMIT_EXCEEDED 说明本次请求超过只读工具预算；
   INVALID_ARGUMENT 请求用户修正参数。
5. items 为空表示查询成功但没有匹配数据。
6. 对普通闲聊直接回答，不调用业务工具。
""".strip()


def build_model(
    settings: Settings,
    client: AsyncOpenAI,
) -> OpenAIChatCompletionsModel:
    return OpenAIChatCompletionsModel(
        model=settings.model_name,
        openai_client=client,
    )


def build_client(settings: Settings) -> AsyncOpenAI:
    settings.assert_model_configured()
    client_kwargs: dict[str, str | float] = {
        "api_key": settings.model_api_key,
        "timeout": settings.agent_run_timeout_seconds,
    }
    if settings.model_base_url.strip():
        client_kwargs["base_url"] = settings.model_base_url
    return AsyncOpenAI(**client_kwargs)


def build_agent(
    settings: Settings,
    client: AsyncOpenAI,
) -> Agent[AgentRequestContext]:
    return Agent[AgentRequestContext](
        name="Internship Task Query Agent",
        instructions=INSTRUCTIONS,
        model=build_model(settings, client),
        tools=[query_internship_tasks],
    )


async def run_agent_query(
    question: str,
    *,
    authorization: str | None,
    tenant_id: str,
    settings: Settings | None = None,
) -> AgentQueryResponse:
    settings = settings or get_settings()
    trace = TraceCollector()
    context = AgentRequestContext(
        authorization=authorization,
        tenant_id=tenant_id,
        yudao_client=YudaoClient(
            settings.yudao_base_url,
            settings.yudao_timeout_seconds,
        ),
        trace=trace,
    )
    client = build_client(settings)
    try:
        result = await asyncio.wait_for(
            Runner.run(
                build_agent(settings, client),
                input=question,
                context=context,
                max_turns=3,
                run_config=RunConfig(
                    tracing_disabled=settings.disable_sdk_tracing,
                    trace_include_sensitive_data=False,
                    tool_execution=ToolExecutionConfig(
                        max_function_tool_concurrency=1,
                    ),
                ),
            ),
            timeout=settings.agent_run_timeout_seconds,
        )
    finally:
        await client.close()
    return AgentQueryResponse(
        answer=str(result.final_output),
        trace=trace.snapshot(),
    )
