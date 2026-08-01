from time import monotonic

from internship_task_agent.schemas import ToolTrace


class TraceCollector:
    """Collect a small, request-local, secret-free tool trace."""

    def __init__(self) -> None:
        self._entries: list[ToolTrace] = []

    def start(self) -> float:
        return monotonic()

    def append(
        self,
        *,
        started_at: float,
        tool_name: str,
        arguments: dict[str, object],
        status: str,
        result_summary: str,
    ) -> None:
        self._entries.append(
            ToolTrace(
                sequence=len(self._entries) + 1,
                tool_name=tool_name,
                arguments=arguments,
                status=status,
                duration_ms=max(0, round((monotonic() - started_at) * 1000)),
                result_summary=result_summary,
            )
        )

    def snapshot(self) -> list[ToolTrace]:
        return list(self._entries)
