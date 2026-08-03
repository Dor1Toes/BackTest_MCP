from __future__ import annotations

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from quantforge_mcp.config import get_settings
from quantforge_mcp.db import SQLiteManager
from quantforge_mcp.db.repositories import ArtifactRepository, JobRepository, OhlcvRepository
from quantforge_mcp.resources.compute_resources import register_compute_resources
from quantforge_mcp.resources.strategy_resources import register_strategy_resources
from quantforge_mcp.services.backtest_service import BacktestService
from quantforge_mcp.services.data_service import DataService
from quantforge_mcp.services.report_service import ReportService
from quantforge_mcp.services.signal_monitor_service import SignalMonitorService
from quantforge_mcp.tools import (
    register_backtest_tools,
    register_data_tools,
    register_monitor_tools,
)

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

settings = get_settings()
manager = SQLiteManager(settings.db_abspath(), _ROOT / "db" / "schema.sql")
manager.init_schema()

ohlcv_repo = OhlcvRepository(manager.connect)
job_repo = JobRepository(manager.connect)
artifact_repo = ArtifactRepository(manager.connect)

data_service = DataService(
    ohlcv_repo,
    data_source=settings.data_source,
    akshare_adjust=settings.akshare_adjust,
    allow_synthetic_fallback=settings.allow_synthetic_fallback,
)
backtest_service = BacktestService(
    settings=settings,
    workspace_root=_ROOT,
    data_service=data_service,
    job_repo=job_repo,
    artifact_repo=artifact_repo,
)
report_service = ReportService(artifact_repo)
signal_monitor_service = SignalMonitorService(settings=settings, data_service=data_service)

mcp = FastMCP("quantforge")
register_data_tools(mcp, data_service)
register_backtest_tools(mcp, backtest_service, report_service)
register_monitor_tools(mcp, signal_monitor_service)
register_compute_resources(mcp)
register_strategy_resources(mcp)


@mcp.resource("quantforge://codegen/spec")
def codegen_spec() -> str:
    return (_ROOT / "resources" / "codegen_spec.md").read_text(encoding="utf-8")


@mcp.resource("quantforge://data/symbol-guide")
def symbol_guide() -> str:
    return (_ROOT / "resources" / "symbol_guide.md").read_text(encoding="utf-8")


@mcp.resource("quantforge://examples/nvda_dynamic_config")
def nvda_example() -> str:
    return """{
  "name": "nvda_dynamic_strategy",
  "symbols": ["NVDA"],
  "start": "2024-01-01",
  "end": "2025-01-01",
  "initial_capital": 100000,
  "commission": 0.0003,
  "slippage": 0.001
}"""


def main() -> None:
    if settings.transport == "sse":
        # NOTE: In some mcp versions, FastMCP.run() does not accept host/port.
        # We always serve the Starlette app with uvicorn for compatibility.
        import uvicorn

        print(f"[quantforge-mcp] started transport=sse host=127.0.0.1 port={settings.sse_port}", flush=True)
        uvicorn.run(mcp.sse_app(), host="127.0.0.1", port=int(settings.sse_port), log_level="info")
    else:
        print("[quantforge-mcp] started transport=stdio", flush=True)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
