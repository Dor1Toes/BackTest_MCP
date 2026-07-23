from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchor default storage paths to this package root (same dir as server.py),
_PROJECT_ROOT = Path(__file__).resolve().parent


def _resolve_storage_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (_PROJECT_ROOT / candidate).resolve()


class MCPSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QUANTFORGE_", extra="ignore")

    db_path: str = "storage/db/quantforge.db"
    artifacts_dir: str = "storage/artifacts"

    data_source: str = "auto"
    akshare_adjust: str = "qfq"
    allow_synthetic_fallback: bool = True

    # local worker subprocess timeout
    sandbox_timeout_sec: int = 120

    transport: str = "stdio"
    sse_port: int = 8001

    def db_abspath(self) -> Path:
        return _resolve_storage_path(self.db_path)

    def artifacts_abspath(self) -> Path:
        return _resolve_storage_path(self.artifacts_dir)


def get_settings() -> MCPSettings:
    settings = MCPSettings()
    settings.db_abspath().parent.mkdir(parents=True, exist_ok=True)
    settings.artifacts_abspath().mkdir(parents=True, exist_ok=True)
    return settings
