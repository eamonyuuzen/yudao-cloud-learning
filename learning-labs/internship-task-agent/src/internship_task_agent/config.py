from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Machine-specific configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    yudao_base_url: str = "http://localhost:48080/admin-api"
    # Must stay below the function-tool timeout (12s).
    yudao_timeout_seconds: float = Field(default=10.0, gt=0, le=10)
    agent_run_timeout_seconds: float = Field(default=45.0, gt=0, le=120)

    model_name: str = ""
    model_api_key: str = ""
    model_base_url: str = ""
    disable_sdk_tracing: bool = True

    def assert_model_configured(self) -> None:
        if not self.model_name.strip():
            raise ValueError("MODEL_NAME 未配置")
        if not self.model_api_key.strip():
            raise ValueError("MODEL_API_KEY 未配置")


@lru_cache
def get_settings() -> Settings:
    return Settings()
