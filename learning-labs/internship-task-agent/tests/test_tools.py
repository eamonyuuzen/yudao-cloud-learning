import httpx
import pytest

from internship_task_agent.context import AgentRequestContext
from internship_task_agent.schemas import (
    QueryInternshipTasksArgs,
    ToolErrorCode,
)
from internship_task_agent.tools import (
    query_internship_tasks,
    query_internship_tasks_impl,
    tool_failure_error,
    tool_timeout_error,
)
from agents import ModelBehaviorError, RunContextWrapper
from agents.tool_context import ToolContext
from internship_task_agent.trace import TraceCollector
from internship_task_agent.yudao_client import YudaoClient


@pytest.mark.asyncio
async def test_tool_returns_data_and_trace() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {"list": [], "total": 0},
                "msg": "",
            },
        )

    trace = TraceCollector()
    context = AgentRequestContext(
        authorization="Bearer test-token",
        tenant_id="1",
        yudao_client=YudaoClient(
            "http://yudao.test/admin-api",
            1,
            transport=httpx.MockTransport(handler),
        ),
        trace=trace,
    )

    result = await query_internship_tasks_impl(
        context,
        QueryInternshipTasksArgs(status=1),
    )

    assert result.ok is True
    assert result.data is not None
    assert result.data.items == []
    assert trace.snapshot()[0].status == "SUCCESS"
    assert trace.snapshot()[0].arguments == {
        "status": 1,
        "page_no": 1,
        "page_size": 10,
    }


@pytest.mark.asyncio
async def test_tool_preserves_forbidden_semantics() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 403, "msg": "没有该操作权限", "data": None},
        )

    trace = TraceCollector()
    context = AgentRequestContext(
        authorization="Bearer test-token",
        tenant_id="1",
        yudao_client=YudaoClient(
            "http://yudao.test/admin-api",
            1,
            transport=httpx.MockTransport(handler),
        ),
        trace=trace,
    )

    result = await query_internship_tasks_impl(
        context,
        QueryInternshipTasksArgs(),
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error.code == ToolErrorCode.FORBIDDEN
    assert trace.snapshot()[0].status == ToolErrorCode.FORBIDDEN.value


def test_function_tool_schema_exposes_business_constraints() -> None:
    properties = query_internship_tasks.params_json_schema["properties"]

    assert "authorization" not in properties
    assert "tenant_id" not in properties
    assert properties["page_no"]["minimum"] == 1
    assert properties["page_size"]["maximum"] == 50
    assert properties["status"]["anyOf"][0]["enum"] == [0, 1, 2]


def test_tool_failure_is_deterministic_and_does_not_echo_input() -> None:
    trace = TraceCollector()
    context = AgentRequestContext(
        authorization="Bearer secret-token",
        tenant_id="1",
        yudao_client=YudaoClient("http://yudao.test/admin-api", 1),
        trace=trace,
    )

    result = tool_failure_error(
        RunContextWrapper(context),
        ModelBehaviorError(
            "Invalid JSON input for tool query_internship_tasks: raw schema detail"
        ),
    )

    assert ToolErrorCode.INVALID_ARGUMENT.value in result
    assert "raw provider" not in result
    assert "secret-token" not in result
    assert trace.snapshot()[0].status == ToolErrorCode.INVALID_ARGUMENT.value


def test_unexpected_tool_failure_is_not_mislabelled_as_bad_input() -> None:
    trace = TraceCollector()
    context = AgentRequestContext(
        authorization="Bearer secret-token",
        tenant_id="1",
        yudao_client=YudaoClient("http://yudao.test/admin-api", 1),
        trace=trace,
    )

    result = tool_failure_error(
        RunContextWrapper(context),
        RuntimeError("database driver leaked a private detail"),
    )

    assert ToolErrorCode.BACKEND_ERROR.value in result
    assert ToolErrorCode.INVALID_ARGUMENT.value not in result
    assert "private detail" not in result
    assert "secret-token" not in result
    assert trace.snapshot()[0].status == ToolErrorCode.BACKEND_ERROR.value


def test_tool_timeout_uses_stable_retryable_contract_and_trace() -> None:
    trace = TraceCollector()
    context = AgentRequestContext(
        authorization="Bearer secret-token",
        tenant_id="1",
        yudao_client=YudaoClient("http://yudao.test/admin-api", 1),
        trace=trace,
    )

    result = tool_timeout_error(
        RunContextWrapper(context),
        TimeoutError("private timeout detail"),
    )

    assert ToolErrorCode.BACKEND_UNAVAILABLE.value in result
    assert '"retryable": true' in result
    assert "private timeout detail" not in result
    assert trace.snapshot()[0].status == ToolErrorCode.BACKEND_UNAVAILABLE.value


@pytest.mark.asyncio
async def test_request_tool_budget_prevents_a_second_backend_call() -> None:
    backend_calls = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal backend_calls
        backend_calls += 1
        return httpx.Response(
            200,
            json={"code": 0, "data": {"list": [], "total": 0}},
        )

    context = AgentRequestContext(
        authorization="Bearer test-token",
        tenant_id="1",
        yudao_client=YudaoClient(
            "http://yudao.test/admin-api",
            1,
            transport=httpx.MockTransport(handler),
        ),
        trace=TraceCollector(),
    )

    first = await query_internship_tasks_impl(
        context,
        QueryInternshipTasksArgs(),
    )
    second = await query_internship_tasks_impl(
        context,
        QueryInternshipTasksArgs(page_no=2),
    )

    assert first.ok is True
    assert second.ok is False
    assert second.error is not None
    assert second.error.code == ToolErrorCode.TOOL_LIMIT_EXCEEDED
    assert backend_calls == 1
    assert context.trace.snapshot()[1].status == (
        ToolErrorCode.TOOL_LIMIT_EXCEEDED.value
    )


@pytest.mark.asyncio
async def test_decorated_tool_maps_invalid_arguments() -> None:
    context = AgentRequestContext(
        authorization="Bearer secret-token",
        tenant_id="1",
        yudao_client=YudaoClient("http://yudao.test/admin-api", 1),
        trace=TraceCollector(),
    )
    raw_arguments = '{"status":99,"page_size":1000}'
    tool_context = ToolContext(
        context,
        tool_name="query_internship_tasks",
        tool_call_id="call-test",
        tool_arguments=raw_arguments,
    )

    result = await query_internship_tasks.on_invoke_tool(
        tool_context,
        raw_arguments,
    )

    assert ToolErrorCode.INVALID_ARGUMENT.value in result
    assert "secret-token" not in result
    assert context.trace.snapshot()[0].status == (
        ToolErrorCode.INVALID_ARGUMENT.value
    )
