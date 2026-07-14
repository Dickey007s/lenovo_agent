from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_cors_origins: str = "http://localhost:3000"
    langgraph_checkpoint_dsn: str = ""
    database_dsn: str = ""
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "deepseek-v4-pro"
    llm_timeout_seconds: float = 60
    llm_thinking_mode: str = "disabled"
    policy_version: str = "2026-07-v1"
    permit_private_key_path: str = ""
    permit_public_key_path: str = ""
    permit_ttl_seconds: int = 300
    tool_mode: str = "simulator"
    log_level: str = "INFO"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
