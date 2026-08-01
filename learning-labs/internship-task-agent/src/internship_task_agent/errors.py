from internship_task_agent.schemas import ToolErrorCode


class YudaoApiError(RuntimeError):
    def __init__(
        self,
        code: ToolErrorCode,
        message: str,
        *,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
