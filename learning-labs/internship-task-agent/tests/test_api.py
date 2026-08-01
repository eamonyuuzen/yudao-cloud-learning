import httpx
import pytest

import internship_task_agent.api as api_module
from internship_task_agent.api import app
from internship_task_agent.errors import YudaoApiError
from internship_task_agent.schemas import (
    AgentQueryResponse,
    ToolErrorCode,
)


@pytest.mark.asyncio
async def test_health_and_required_header_boundaries() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://agent.test",
    ) as client:
        health = await client.get("/health")
        missing_auth = await client.post(
            "/agent/query",
            json={"question": "查询任务"},
        )
        malformed_auth = await client.post(
            "/agent/query",
            headers={
                "Authorization": "not-a-bearer-token",
                "tenant-id": "1",
            },
            json={"question": "查询任务"},
        )
        missing_tenant = await client.post(
            "/agent/query",
            headers={"Authorization": "Bearer test-token"},
            json={"question": "查询任务"},
        )

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert missing_auth.status_code == 401
    assert missing_auth.json() == {"detail": "缺少 Authorization"}
    assert malformed_auth.status_code == 401
    assert malformed_auth.json() == {
        "detail": "Authorization 格式不正确"
    }
    assert missing_tenant.status_code == 400
    assert missing_tenant.json() == {"detail": "缺少 tenant-id"}


@pytest.mark.asyncio
async def test_invalid_session_does_not_spend_model_call(monkeypatch) -> None:
    model_called = False

    async def reject_session(**_: object) -> None:
        raise YudaoApiError(
            ToolErrorCode.UNAUTHENTICATED,
            "登录状态无效或已过期，请重新登录。",
        )

    async def fake_run(*_: object, **__: object) -> AgentQueryResponse:
        nonlocal model_called
        model_called = True
        return AgentQueryResponse(answer="unexpected", trace=[])

    monkeypatch.setattr(
        api_module,
        "authenticate_before_model",
        reject_session,
    )
    monkeypatch.setattr(api_module, "run_agent_query", fake_run)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://agent.test",
    ) as client:
        response = await client.post(
            "/agent/query",
            headers={
                "Authorization": "Bearer invalid-token",
                "tenant-id": "1",
            },
            json={"question": "解释事务"},
        )

    assert response.status_code == 401
    assert model_called is False
