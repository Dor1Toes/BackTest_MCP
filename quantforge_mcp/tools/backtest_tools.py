from __future__ import annotations

import anyio.to_thread

from quantforge_mcp.codegen import BacktestConfigError, load_backtest_config
from quantforge_mcp.services.backtest_service import BacktestService
from quantforge_mcp.services.report_service import ReportService


def register_backtest_tools(mcp, backtest_service: BacktestService, report_service: ReportService) -> None:
    @mcp.tool()
    async def run_backtest_dynamic(code: str, config_json: str) -> dict:
        """Run a dynamic Strategy backtest in an isolated sandbox and persist artifacts.

        Args:
            code: Python source with exactly one `Strategy` subclass. Strategy rules and
                allowed imports are enforced before execution; see `quantforge://codegen/spec`.
            config_json: JSON string for backtest settings (required: `symbols`; optional:
                `name`, `start`, `end`, `initial_capital`, `commission`, `slippage`,
                `target_weights`, `sizing_fraction`, `rebalance`, `last_rebalance_ts`,
                `history_tail`). Dates must be YYYY-MM-DD. Full schema and examples:
                `quantforge://codegen/spec`.

        Returns:
            On success: `{"ok": true, "job_id": str, "status": "done", "result": {...}}`
            where `result` includes `metrics` (total_return, max_drawdown, n_trades, ...).
            On validation failure: `{"ok": false, "validation": {...}}` (no job created).
            On runtime failure: `{"ok": false, "job_id": str, "status": "failed", "error": str}`.
        """
        try:
            config = load_backtest_config(config_json=config_json)
        except BacktestConfigError as exc:
            return {"ok": False, "validation": exc.to_validation_dict()}

        def _run() -> dict:
            return backtest_service.run_dynamic(code=code, config=config)

        return await anyio.to_thread.run_sync(_run)

    @mcp.tool()
    def get_backtest_result(job_id: str) -> dict:
        """Fetch status and summary for a backtest job stored in SQLite.

        Args:
            job_id: Job identifier returned by `run_backtest_dynamic`.

        Returns:
            `{"ok": true, "job_id": str, "status": str, "job_type": str,
            "error_message": str|null, "result": dict|null}` where `result` holds
            metrics and metadata when `status` is `"done"`. On unknown job:
            `{"ok": false, "error": str}`.
        """
        return backtest_service.get_result(job_id)

    @mcp.tool()
    def list_backtest_jobs(limit: int = 50, status: str = "") -> dict:
        """List recent backtest jobs from SQLite, newest first.

        Args:
            limit: Maximum number of jobs to return (default 50).
            status: Optional filter, e.g. `"done"` or `"failed"`; empty string returns all.

        Returns:
            `{"ok": true, "count": int, "jobs": [...]}` where each job includes
            `job_id`, `status`, `strategy_name`, `symbols`, `start`, `end`,
            `total_return`, `max_drawdown`, `n_trades`, timestamps, and `error_message`.
        """
        return backtest_service.list_jobs(limit=limit, status=status)

    @mcp.tool()
    def generate_backtest_report(job_id: str, title: str = "") -> dict:
        """Build a Markdown tearsheet report from a completed backtest's equity curve.

        Args:
            job_id: Completed backtest job (must have an `equity_curve` artifact).
            title: Optional report heading; defaults to `"Backtest {job_id}"`.

        Returns:
            On success: `{"ok": true, "job_id": str, "title": str, "format": "markdown",
            "path": str, "content": str}`. Also registers a `report_markdown` artifact.
            On missing equity curve: `{"ok": false, "error": str}`.
        """
        return report_service.generate(job_id=job_id, title=title)

    @mcp.tool()
    def get_backtest_artifacts(job_id: str, kind: str = "") -> dict:
        """List on-disk artifact paths for a backtest job.

        Args:
            job_id: Backtest job identifier.
            kind: Optional filter: `equity_curve`, `trades`, `stdout`, `stderr`,
                `strategy_code`, or `report_markdown`; empty returns all kinds.

        Returns:
            `{"ok": true, "job_id": str, "artifacts": [{"kind": str, "path": str, ...}]}`.
        """
        return backtest_service.get_artifacts(job_id=job_id, kind=(kind or None))
