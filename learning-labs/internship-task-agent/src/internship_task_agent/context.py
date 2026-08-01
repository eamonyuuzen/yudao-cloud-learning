from dataclasses import dataclass

from internship_task_agent.trace import TraceCollector
from internship_task_agent.yudao_client import YudaoClient


@dataclass(slots=True)
class AgentRequestContext:
    """Data valid only during one incoming Agent request."""

    authorization: str | None
    tenant_id: str
    yudao_client: YudaoClient
    trace: TraceCollector
    max_tool_calls: int = 1
    tool_call_count: int = 0

    def reserve_tool_call(self) -> bool:
        """Reserve one deterministic backend call for this Agent run."""

        self.tool_call_count += 1
        return self.tool_call_count <= self.max_tool_calls
