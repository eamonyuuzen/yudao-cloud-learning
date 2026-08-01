import json
from typing import Annotated, Literal

from agents import ModelBehaviorError, RunContextWrapper, function_tool
from pydantic import Field

from internship_task_agent.context import AgentRequestContext
from internship_task_agent.errors import YudaoApiError
from internship_task_agent.schemas import (
    QueryInternshipTasksArgs,
    QueryToolResult,
    ToolError,
    ToolErrorCode,
)

TOOL_NAME = "query_internship_tasks"


def _error_json(
    code: ToolErrorCode,
    message: str,
    *,
    retryable: bool = False,
) -> str:
    result = QueryToolResult(
        ok=False,
        error=ToolError(
            code=code,
            message=message,
            retryable=retryable,
        ),
    )
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False)


def tool_failure_error(
    ctx: RunContextWrapper[AgentRequestContext],
    error: Exception,
) -> str:
    """Turn SDK/tool failures into deterministic, non-sensitive results."""

    invalid_arguments = isinstance(error, ModelBehaviorError) and str(error).startswith(
        "Invalid JSON input for tool"
    )

    code = (
        ToolErrorCode.INVALID_ARGUMENT
        if invalid_arguments
        else ToolErrorCode.BACKEND_ERROR
    )
    message = (
        "工具参数不符合契约，请修正后重试。"
        if invalid_arguments
        else "工具执行失败，请稍后重试。"
    )
    started_at = ctx.context.trace.start()
    ctx.context.trace.append(
        started_at=started_at,
        tool_name=TOOL_NAME,
        arguments={},
        status=code.value,
        result_summary=message,
    )
    return _error_json(code, message)


def tool_timeout_error(
    ctx: RunContextWrapper[AgentRequestContext],
    _: Exception,
) -> str:
    """Return the same stable contract when the SDK cancels a slow tool."""

    message = "实习任务查询超时，请稍后重试。"
    started_at = ctx.context.trace.start()
    ctx.context.trace.append(
        started_at=started_at,
        tool_name=TOOL_NAME,
        arguments={},
        status=ToolErrorCode.BACKEND_UNAVAILABLE.value,
        result_summary=message,
    )
    return _error_json(
        ToolErrorCode.BACKEND_UNAVAILABLE,
        message,
        retryable=True,
    )


async def query_internship_tasks_impl(
    context: AgentRequestContext,
    args: QueryInternshipTasksArgs,
) -> QueryToolResult:
    """Framework-light implementation that can be tested without a model."""

    started_at = context.trace.start()
    safe_arguments = args.model_dump(exclude_none=True)
    if not context.reserve_tool_call():
        message = "本次请求已达到只读工具调用上限。"
        context.trace.append(
            started_at=started_at,
            tool_name=TOOL_NAME,
            arguments=safe_arguments,
            status=ToolErrorCode.TOOL_LIMIT_EXCEEDED.value,
            result_summary=message,
        )
        return QueryToolResult(
            ok=False,
            error=ToolError(
                code=ToolErrorCode.TOOL_LIMIT_EXCEEDED,
                message=message,
            ),
        )

    try:
        page = await context.yudao_client.query_internship_tasks(
            args,
            authorization=context.authorization,
            tenant_id=context.tenant_id,
        )
    except YudaoApiError as exc:
        context.trace.append(
            started_at=started_at,
            tool_name=TOOL_NAME,
            arguments=safe_arguments,
            status=exc.code.value,
            result_summary=exc.message,
        )
        return QueryToolResult(
            ok=False,
            error=ToolError(
                code=exc.code,
                message=exc.message,
                retryable=exc.retryable,
            ),
        )

    context.trace.append(
        started_at=started_at,
        tool_name=TOOL_NAME,
        arguments=safe_arguments,
        status="SUCCESS",
        result_summary=f"total={page.total}, returned={len(page.items)}",
    )
    return QueryToolResult(ok=True, data=page)


@function_tool(
    failure_error_function=tool_failure_error,
    timeout=12,
    timeout_error_function=tool_timeout_error,
)
async def query_internship_tasks(
    ctx: RunContextWrapper[AgentRequestContext],
    title: Annotated[str | None, Field(max_length=200)] = None,
    status: Literal[0, 1, 2] | None = None,
    page_no: Annotated[int, Field(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Field(ge=1, le=50)] = 10,
) -> str:
    """通过 Yudao 正式接口，按标题和状态分页查询实习任务。

    Args:
        title: 任务标题的模糊匹配文本，不需要时留空。
        status: 0 待处理、1 进行中、2 已完成，不筛选时留空。
        page_no: 页码，从 1 开始。
        page_size: 每页数量，范围 1 到 50。
    """

    args = QueryInternshipTasksArgs(
        title=title,
        status=status,
        page_no=page_no,
        page_size=page_size,
    )
    result = await query_internship_tasks_impl(ctx.context, args)
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
