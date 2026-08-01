from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QueryInternshipTasksArgs(BaseModel):
    """Arguments the model is allowed to choose for the read-only tool."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(
        default=None,
        max_length=200,
        description="任务标题中的模糊匹配文本；不需要标题条件时留空。",
    )
    status: Literal[0, 1, 2] | None = Field(
        default=None,
        description="任务状态：0 待处理，1 进行中，2 已完成；不筛选状态时留空。",
    )
    page_no: int = Field(default=1, ge=1, le=10_000)
    page_size: int = Field(default=10, ge=1, le=50)


class InternshipTask(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    title: str
    deadline: datetime | None = None
    status: Literal[0, 1, 2]


class InternshipTaskPage(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    items: list[InternshipTask] = Field(alias="list")
    total: int = Field(ge=0)


class ToolErrorCode(str, Enum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    TOOL_LIMIT_EXCEEDED = "TOOL_LIMIT_EXCEEDED"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    BACKEND_ERROR = "BACKEND_ERROR"


class ToolError(BaseModel):
    code: ToolErrorCode
    message: str
    retryable: bool = False


class QueryToolResult(BaseModel):
    ok: bool
    data: InternshipTaskPage | None = None
    error: ToolError | None = None


class ToolTrace(BaseModel):
    sequence: int
    tool_name: str
    arguments: dict[str, object]
    status: str
    duration_ms: int
    result_summary: str


class AgentQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1_000)


class AgentQueryResponse(BaseModel):
    answer: str
    trace: list[ToolTrace]
