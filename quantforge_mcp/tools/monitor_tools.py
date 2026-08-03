from __future__ import annotations

import anyio.to_thread

from quantforge_mcp.codegen import BacktestConfigError, load_backtest_config
from quantforge_mcp.services.signal_monitor_service import SignalMonitorService


def register_monitor_tools(mcp, monitor_service: SignalMonitorService) -> None:
    @mcp.tool()
    async def scan_strategy_signals(
        job_id: str,
        warmup_days_override: int | None = None,
        notify: bool = True,
        notify_to: str | None = None,
    ) -> dict:
        """Scan the latest bar for live strategy signals from a saved backtest job.

        Loads `strategy.py` and `config.json` from `storage/artifacts/{job_id}/`.
        Fetches recent OHLCV through today; the calendar-day window is derived from
        `strategy.warmup()` unless overridden.

        Args:
            job_id: Backtest job whose artifacts contain the strategy and config.
            warmup_days_override: Optional calendar days of history to fetch; overrides
                the default warmup-based window when set.
            notify: When true and signals exist, send email via configured SMTP
                (`QUANTFORGE_SMTP_*` / `QUANTFORGE_NOTIFY_*` env vars).
            notify_to: Optional recipient override; defaults to `QUANTFORGE_NOTIFY_TO`.

        Returns:
            `{"ok": bool, "strategy_name": str, "symbols": [...], "data_range": {...},
            "signals": [{symbol, direction, strength, strategy_id, bar_date, close}],
            "warnings": [...], "notified": bool, "notify_error": str|null}`.
            On missing files or invalid config: `{"ok": false, "error": str}` or
            `{"ok": false, "validation": {...}}`. Config fields (`rebalance`,
            `last_rebalance_ts`, `history_tail`) follow `quantforge://codegen/spec`.
        """
        try:
            strat_path, cfg_path = monitor_service.resolve_job_paths(job_id)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        if not strat_path.is_file():
            return {"ok": False, "error": f"strategy file not found: {strat_path}"}
        if not cfg_path.is_file():
            return {"ok": False, "error": f"config file not found: {cfg_path}"}

        try:
            config = load_backtest_config(source=cfg_path)
        except BacktestConfigError as exc:
            return {"ok": False, "validation": exc.to_validation_dict()}

        def _run() -> dict:
            result = monitor_service.scan(
                strategy_path=strat_path,
                config=config,
                warmup_days_override=warmup_days_override,
                notify=notify,
                notify_to=notify_to,
            )
            return result.model_dump()

        return await anyio.to_thread.run_sync(_run)
