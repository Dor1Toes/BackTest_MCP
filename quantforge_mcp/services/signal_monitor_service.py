from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from quantforge_mcp.config import MCPSettings
from quantforge_mcp.monitor.notifiers.email import EmailNotifier
from quantforge_mcp.monitor.signal_scanner import SignalScanner
from quantforge_mcp.codegen import StrategyLoadError, load_strategy
from quantforge_mcp.schemas.monitor import ScanResult, SignalInfo
from quantforge_mcp.schemas.config import BacktestConfig
from quantforge_mcp.services.data_service import DataService
from quantforge_stock.core.event import SignalEvent


def calendar_days_for_warmup(warmup_bars: int, warmup_days_override: int | None = None) -> int:
    if warmup_days_override is not None:
        return max(1, int(warmup_days_override))
    return int(warmup_bars * 7 / 5) + 15


class SignalMonitorService:
    def __init__(
        self,
        *,
        settings: MCPSettings,
        data_service: DataService,
    ) -> None:
        self._settings = settings
        self._data_service = data_service
        self._scanner = SignalScanner()
        self._notifier = EmailNotifier(settings)

    def resolve_job_paths(self, job_id: str) -> tuple[Path, Path]:
        job_id = (job_id or "").strip()
        if not job_id:
            raise ValueError("job_id is required")
        job_dir = self._settings.artifacts_abspath() / job_id
        return job_dir / "strategy.py", job_dir / "config.json"

    def scan(
        self,
        *,
        strategy_path: Path,
        config: BacktestConfig,
        warmup_days_override: int | None = None,
        notify: bool = True,
        notify_to: str | None = None,
    ) -> ScanResult:
        try:
            strategy = load_strategy(source=strategy_path)
        except StrategyLoadError as exc:
            validation = exc.validation.to_dict() if exc.validation else None
            return ScanResult(
                ok=False,
                strategy_name=config.name,
                symbols=list(config.symbols),
                data_range={},
                warnings=[str(exc)],
                validation=validation,
                notify_error=None,
            )
        warmup_bars = strategy.warmup()
        end_d = date.today().isoformat()
        calendar_days = calendar_days_for_warmup(warmup_bars, warmup_days_override)
        start_d = (date.today() - timedelta(days=calendar_days)).isoformat()

        data: dict[str, pd.DataFrame] = {}
        for symbol in config.symbols:
            frame, _ = self._data_service.get_ohlcv(symbol, start_d, end_d)
            data[symbol] = frame

        output = self._scanner.scan(
            strategy=strategy,
            data=data,
            rebalance=config.rebalance,
            last_rebalance_ts=config.last_rebalance_ts,
            history_tail=config.history_tail,
        )

        signal_infos = self._to_signal_infos(output.signals, output.bar_dates, output.closes)
        strategy_name = getattr(strategy, "name", config.name)

        result = ScanResult(
            ok=True,
            strategy_name=strategy_name,
            symbols=list(config.symbols),
            data_range={
                "start": start_d,
                "end": end_d,
                "warmup_bars": warmup_bars,
                "calendar_days": calendar_days,
                "latest_bar": output.latest_bar or "",
            },
            signals=signal_infos,
            warnings=output.warnings,
            notified=False,
            notify_error=None,
        )

        if notify and signal_infos:
            try:
                self._notifier.send(
                    strategy_name=strategy_name,
                    signals=signal_infos,
                    notify_to=notify_to,
                )
                result.notified = True
            except Exception as exc:
                result.notify_error = str(exc)

        return result

    @staticmethod
    def _to_signal_infos(
        signals: list[SignalEvent],
        bar_dates: dict[str, str],
        closes: dict[str, float],
    ) -> list[SignalInfo]:
        infos: list[SignalInfo] = []
        for sig in signals:
            symbol = sig.symbol
            bar_date = bar_dates.get(symbol, "")
            if hasattr(sig.timestamp, "strftime"):
                bar_date = bar_date or sig.timestamp.strftime("%Y-%m-%d")
            else:
                bar_date = bar_date or str(sig.timestamp)
            close = closes.get(symbol, 0.0)
            infos.append(
                SignalInfo(
                    symbol=symbol,
                    direction=int(sig.direction),
                    strength=float(sig.strength),
                    strategy_id=str(sig.strategy_id),
                    bar_date=bar_date,
                    close=close,
                )
            )
        return infos
