from collections.abc import Mapping
from typing import Any

import httpx
from pydantic import ValidationError

from internship_task_agent.errors import YudaoApiError
from internship_task_agent.schemas import (
    InternshipTaskPage,
    QueryInternshipTasksArgs,
    ToolErrorCode,
)


class YudaoClient:
    """Narrow adapter for the existing Yudao internship-task API."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout_seconds)
        self._transport = transport

    async def query_internship_tasks(
        self,
        args: QueryInternshipTasksArgs,
        *,
        authorization: str | None,
        tenant_id: str,
    ) -> InternshipTaskPage:
        if not authorization or not authorization.strip():
            raise YudaoApiError(
                ToolErrorCode.UNAUTHENTICATED,
                "缺少 Authorization，请重新登录。",
            )

        params: dict[str, str | int] = {
            "pageNo": args.page_no,
            "pageSize": args.page_size,
        }
        if args.title:
            params["title"] = args.title
        if args.status is not None:
            params["status"] = args.status

        headers = {
            "Authorization": authorization,
            "tenant-id": tenant_id,
        }

        response = await self._get(
            "/system/internship-task/page",
            headers=headers,
            params=params,
        )
        payload = self._parse_common_result(response)

        data = payload.get("data")
        if not isinstance(data, Mapping):
            raise YudaoApiError(
                ToolErrorCode.BACKEND_ERROR,
                "Yudao 返回的数据结构不正确。",
            )
        try:
            return InternshipTaskPage.model_validate(data)
        except ValidationError as exc:
            raise YudaoApiError(
                ToolErrorCode.BACKEND_ERROR,
                "Yudao 返回的数据结构不正确。",
            ) from exc

    async def validate_session(
        self,
        *,
        authorization: str,
        tenant_id: str,
    ) -> None:
        """Reject an invalid session before spending a model request."""

        response = await self._get(
            "/system/auth/get-permission-info",
            headers={
                "Authorization": authorization,
                "tenant-id": tenant_id,
            },
        )
        payload = self._parse_common_result(response)
        data = payload.get("data")
        user = data.get("user") if isinstance(data, Mapping) else None
        try:
            user_id = int(user["id"]) if isinstance(user, Mapping) else 0
        except (KeyError, TypeError, ValueError):
            user_id = 0
        if user_id <= 0:
            raise YudaoApiError(
                ToolErrorCode.UNAUTHENTICATED,
                "登录状态无效或已过期，请重新登录。",
            )

    async def _get(
        self,
        path: str,
        *,
        headers: dict[str, str],
        params: dict[str, str | int] | None = None,
    ) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                return await client.get(
                    f"{self._base_url}{path}",
                    params=params,
                    headers=headers,
                )
        except httpx.RequestError as exc:
            raise YudaoApiError(
                ToolErrorCode.BACKEND_UNAVAILABLE,
                "Yudao 暂时不可用。",
                retryable=True,
            ) from exc

    @classmethod
    def _parse_common_result(
        cls,
        response: httpx.Response,
    ) -> dict[str, Any]:
        # HTTP 状态先于响应体判断：网关可能返回空的 401/403/500。
        if response.status_code == 401:
            raise YudaoApiError(
                ToolErrorCode.UNAUTHENTICATED,
                "登录状态无效或已过期，请重新登录。",
            )
        if response.status_code == 403:
            raise YudaoApiError(
                ToolErrorCode.FORBIDDEN,
                "当前账号没有执行该操作的权限。",
            )
        if response.status_code >= 500:
            raise YudaoApiError(
                ToolErrorCode.BACKEND_UNAVAILABLE,
                "Yudao 暂时不可用。",
                retryable=True,
            )

        payload = cls._parse_payload(response)
        try:
            code = int(payload["code"])
        except (KeyError, TypeError, ValueError) as exc:
            raise YudaoApiError(
                ToolErrorCode.BACKEND_ERROR,
                "Yudao 返回的数据结构不正确。",
            ) from exc

        if code == 401:
            raise YudaoApiError(
                ToolErrorCode.UNAUTHENTICATED,
                "登录状态无效或已过期，请重新登录。",
            )
        if code == 403:
            raise YudaoApiError(
                ToolErrorCode.FORBIDDEN,
                "当前账号没有执行该操作的权限。",
            )
        if code == 500:
            raise YudaoApiError(
                ToolErrorCode.BACKEND_UNAVAILABLE,
                "Yudao 暂时不可用。",
                retryable=True,
            )
        if response.status_code >= 400 or code != 0:
            raise YudaoApiError(
                ToolErrorCode.BACKEND_ERROR,
                "Yudao 请求失败。",
            )
        return payload

    @staticmethod
    def _parse_payload(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise YudaoApiError(
                ToolErrorCode.BACKEND_ERROR,
                "Yudao 返回的不是 JSON。",
            ) from exc
        if not isinstance(payload, dict):
            raise YudaoApiError(
                ToolErrorCode.BACKEND_ERROR,
                "Yudao 返回的数据结构不正确。",
            )
        return payload
