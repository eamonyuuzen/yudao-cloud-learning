import httpx
import pytest

from internship_task_agent.errors import YudaoApiError
from internship_task_agent.schemas import (
    QueryInternshipTasksArgs,
    ToolErrorCode,
)
from internship_task_agent.yudao_client import YudaoClient


@pytest.mark.asyncio
async def test_query_maps_yudao_page() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.headers["tenant-id"] == "1"
        assert request.url.params["title"] == "用户"
        assert request.url.params["status"] == "1"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "msg": "",
                "data": {
                    "list": [
                        {
                            "id": 10,
                            "title": "用户权限任务",
                            "description": None,
                            "deadline": "2026-08-01T12:00:00",
                            "status": 1,
                        }
                    ],
                    "total": 1,
                },
            },
        )

    client = YudaoClient(
        "http://yudao.test/admin-api",
        1,
        transport=httpx.MockTransport(handler),
    )
    page = await client.query_internship_tasks(
        QueryInternshipTasksArgs(title="用户", status=1),
        authorization="Bearer test-token",
        tenant_id="1",
    )

    assert page.total == 1
    assert page.items[0].title == "用户权限任务"
    assert "description" not in page.items[0].model_dump()


@pytest.mark.asyncio
async def test_query_does_not_send_http_without_token() -> None:
    called = False

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    client = YudaoClient(
        "http://yudao.test/admin-api",
        1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(YudaoApiError) as error:
        await client.query_internship_tasks(
            QueryInternshipTasksArgs(),
            authorization=None,
            tenant_id="1",
        )

    assert error.value.code == ToolErrorCode.UNAUTHENTICATED
    assert called is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("business_code", "expected"),
    [
        (401, ToolErrorCode.UNAUTHENTICATED),
        (403, ToolErrorCode.FORBIDDEN),
    ],
)
async def test_query_preserves_auth_business_codes(
    business_code: int,
    expected: ToolErrorCode,
) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": business_code,
                "msg": "没有该操作权限",
                "data": None,
            },
        )

    client = YudaoClient(
        "http://yudao.test/admin-api",
        1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(YudaoApiError) as error:
        await client.query_internship_tasks(
            QueryInternshipTasksArgs(),
            authorization="Bearer test-token",
            tenant_id="1",
        )

    assert error.value.code == expected


@pytest.mark.asyncio
async def test_query_maps_timeout_to_retryable_unavailable() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    client = YudaoClient(
        "http://yudao.test/admin-api",
        1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(YudaoApiError) as error:
        await client.query_internship_tasks(
            QueryInternshipTasksArgs(),
            authorization="Bearer test-token",
            tenant_id="1",
        )

    assert error.value.code == ToolErrorCode.BACKEND_UNAVAILABLE
    assert error.value.retryable is True


@pytest.mark.asyncio
async def test_query_maps_protocol_error_to_retryable_unavailable() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.RemoteProtocolError(
            "server disconnected",
            request=request,
        )

    client = YudaoClient(
        "http://yudao.test/admin-api",
        1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(YudaoApiError) as error:
        await client.query_internship_tasks(
            QueryInternshipTasksArgs(),
            authorization="Bearer test-token",
            tenant_id="1",
        )

    assert error.value.code == ToolErrorCode.BACKEND_UNAVAILABLE
    assert error.value.retryable is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("http_status", "expected", "retryable"),
    [
        (401, ToolErrorCode.UNAUTHENTICATED, False),
        (403, ToolErrorCode.FORBIDDEN, False),
        (500, ToolErrorCode.BACKEND_UNAVAILABLE, True),
    ],
)
async def test_query_maps_empty_http_errors_before_json(
    http_status: int,
    expected: ToolErrorCode,
    retryable: bool,
) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(http_status)

    client = YudaoClient(
        "http://yudao.test/admin-api",
        1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(YudaoApiError) as error:
        await client.query_internship_tasks(
            QueryInternshipTasksArgs(),
            authorization="Bearer test-token",
            tenant_id="1",
        )

    assert error.value.code == expected
    assert error.value.retryable is retryable


@pytest.mark.asyncio
async def test_query_maps_invalid_common_result_code() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": "not-a-number", "data": None},
        )

    client = YudaoClient(
        "http://yudao.test/admin-api",
        1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(YudaoApiError) as error:
        await client.query_internship_tasks(
            QueryInternshipTasksArgs(),
            authorization="Bearer test-token",
            tenant_id="1",
        )

    assert error.value.code == ToolErrorCode.BACKEND_ERROR


@pytest.mark.asyncio
async def test_query_maps_invalid_page_shape() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 0, "data": {"list": "wrong", "total": 1}},
        )

    client = YudaoClient(
        "http://yudao.test/admin-api",
        1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(YudaoApiError) as error:
        await client.query_internship_tasks(
            QueryInternshipTasksArgs(),
            authorization="Bearer test-token",
            tenant_id="1",
        )

    assert error.value.code == ToolErrorCode.BACKEND_ERROR


@pytest.mark.asyncio
async def test_validate_session_calls_yudao_before_model() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/system/auth/get-permission-info")
        assert request.headers["Authorization"] == "Bearer test-token"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {"user": {"id": 2}, "permissions": []},
            },
        )

    client = YudaoClient(
        "http://yudao.test/admin-api",
        1,
        transport=httpx.MockTransport(handler),
    )

    await client.validate_session(
        authorization="Bearer test-token",
        tenant_id="1",
    )


@pytest.mark.asyncio
async def test_validate_session_rejects_user_without_positive_id() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 0, "data": {"user": {}, "permissions": []}},
        )

    client = YudaoClient(
        "http://yudao.test/admin-api",
        1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(YudaoApiError) as error:
        await client.validate_session(
            authorization="Bearer test-token",
            tenant_id="1",
        )

    assert error.value.code == ToolErrorCode.UNAUTHENTICATED
