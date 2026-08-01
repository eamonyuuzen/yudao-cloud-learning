import logging

from fastapi import FastAPI, Header, HTTPException

from internship_task_agent.agent import run_agent_query
from internship_task_agent.config import Settings, get_settings
from internship_task_agent.errors import YudaoApiError
from internship_task_agent.schemas import AgentQueryRequest, AgentQueryResponse
from internship_task_agent.schemas import ToolErrorCode
from internship_task_agent.yudao_client import YudaoClient

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Internship Task Agent Lab",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/agent/query", response_model=AgentQueryResponse)
async def query(
    request: AgentQueryRequest,
    authorization: str | None = Header(default=None),
    tenant_id: str | None = Header(default=None, alias="tenant-id"),
) -> AgentQueryResponse:
    if not authorization or not authorization.strip():
        raise HTTPException(status_code=401, detail="缺少 Authorization")
    if not authorization.startswith("Bearer ") or not authorization[7:].strip():
        raise HTTPException(status_code=401, detail="Authorization 格式不正确")
    if not tenant_id or not tenant_id.strip():
        raise HTTPException(status_code=400, detail="缺少 tenant-id")

    settings = get_settings()
    try:
        await authenticate_before_model(
            authorization=authorization,
            tenant_id=tenant_id,
            settings=settings,
        )
        return await run_agent_query(
            request.question,
            authorization=authorization,
            tenant_id=tenant_id,
            settings=settings,
        )
    except YudaoApiError as exc:
        status_code = {
            ToolErrorCode.UNAUTHENTICATED: 401,
            ToolErrorCode.FORBIDDEN: 403,
            ToolErrorCode.BACKEND_UNAVAILABLE: 502,
            ToolErrorCode.BACKEND_ERROR: 502,
        }.get(exc.code, 400)
        raise HTTPException(
            status_code=status_code,
            detail=exc.message,
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Agent 查询失败")
        raise HTTPException(
            status_code=502,
            detail="Agent 或模型服务暂时不可用",
        ) from exc


async def authenticate_before_model(
    *,
    authorization: str,
    tenant_id: str,
    settings: Settings,
) -> None:
    """Use the deterministic backend to authenticate before calling a model."""

    client = YudaoClient(
        settings.yudao_base_url,
        settings.yudao_timeout_seconds,
    )
    await client.validate_session(
        authorization=authorization,
        tenant_id=tenant_id,
    )
