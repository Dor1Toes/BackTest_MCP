from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QUANTFORGE_", extra="ignore")

    db_path: str = "quantforge_mcp/storage/quantforge.db"
    artifacts_dir: str = "quantforge_mcp/storage/artifacts"

    data_source: str = "yfinance"
    allow_synthetic_fallback: bool = True

    docker_image: str = "quantforge-worker:latest"
    docker_enabled: bool = True
    sandbox_timeout_sec: int = 120
    sandbox_mem_limit: str = "512m"
    sandbox_cpu_quota: int = 100_000

    transport: str = "stdio"
    sse_port: int = 8001

    def db_abspath(self) -> Path:
        return Path(self.db_path).resolve()

    def artifacts_abspath(self) -> Path:
        return Path(self.artifacts_dir).resolve()


def get_settings() -> MCPSettings:
    settings = MCPSettings()
    settings.db_abspath().parent.mkdir(parents=True, exist_ok=True)
    settings.artifacts_abspath().mkdir(parents=True, exist_ok=True)
    return settings
