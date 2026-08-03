from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve relative storage paths from current working directory.
# This makes the package runnable via uvx/pipx (site-packages is not writable).
_PROJECT_ROOT = Path.cwd()

def _user_storage_root() -> Path:
    # Allow explicit override (absolute or relative to cwd)
    override = os.getenv("QUANTFORGE_STORAGE_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    # Default to a user-writable location
    base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or ""
    if base:
        return (Path(base) / "quantforge-mcp").resolve()
    return (Path.home() / ".quantforge-mcp").resolve()


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

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_ssl: bool = False
    smtp_use_tls: bool = True
    notify_from: str = ""
    notify_to: str = ""

    def db_abspath(self) -> Path:
        return _resolve_storage_path(self.db_path)

    def artifacts_abspath(self) -> Path:
        return _resolve_storage_path(self.artifacts_dir)


def get_settings() -> MCPSettings:
    settings = MCPSettings()
    global _PROJECT_ROOT
    try:
        settings.db_abspath().parent.mkdir(parents=True, exist_ok=True)
        settings.artifacts_abspath().mkdir(parents=True, exist_ok=True)
    except Exception:
        # If cwd is not writable (e.g. System32), fall back to a user-writable base.
        _PROJECT_ROOT = _user_storage_root()
        settings.db_abspath().parent.mkdir(parents=True, exist_ok=True)
        settings.artifacts_abspath().mkdir(parents=True, exist_ok=True)
    return settings
