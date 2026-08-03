from __future__ import annotations

import anyio.to_thread

from quantforge_mcp.services._formatters import summarize_ohlcv
from quantforge_mcp.services.data_service import DataService


def register_data_tools(mcp, data_service: DataService) -> None:
    @mcp.tool()
    async def get_stock_data(
        symbols: list[str],
        start: str = "",
        end: str = "",
        interval: str = "1d",
        preview: bool = False,
        preview_rows: int = 3,
    ) -> dict:
        """Fetch and cache OHLCV bars for one or more symbols from local DB or remote source.

        Args:
            symbols: Non-empty list of ticker codes; pass a single symbol as `["600519"]`.
                Symbol formats: `quantforge://data/symbol-guide`.
            start: Start date YYYY-MM-DD; empty uses a default lookback window.
            end: End date YYYY-MM-DD; empty defaults to today.
            interval: Bar interval (default `"1d"`).
            preview: When false, returns row counts only; when true, adds stats and head/tail samples.
            preview_rows: Number of head/tail rows per symbol when `preview=True` (default 3).

        Returns:
            `{"ok": true, "start": str, "end": str, "interval": str, "items": [...]}`
            where each item has `symbol`, `rows`, `source`, and optional preview fields.
            On empty symbols: `{"ok": false, "error": str}`.
        """
        if not symbols:
            return {"ok": False, "error": "symbols must not be empty"}

        def _run() -> dict:
            start_d, end_d = data_service.default_dates(start, end)
            items: list[dict] = []
            for symbol in symbols:
                frame, source = data_service.get_ohlcv(
                    symbol=symbol,
                    start=start_d,
                    end=end_d,
                    interval=interval,
                )
                item: dict = {
                    "symbol": symbol,
                    "rows": len(frame),
                    "source": source,
                }
                if preview:
                    summary = summarize_ohlcv(
                        frame,
                        symbol=symbol,
                        start=start_d,
                        end=end_d,
                        preview=max(1, int(preview_rows)),
                    )
                    item.update(
                        {
                            "stats": summary.stats,
                            "preview_head": [x.model_dump() for x in summary.head],
                            "preview_tail": [x.model_dump() for x in summary.tail],
                            "missing_pct": summary.missing_pct,
                        }
                    )
                items.append(item)
            return {
                "ok": True,
                "start": start_d,
                "end": end_d,
                "interval": interval,
                "items": items,
            }

        return await anyio.to_thread.run_sync(_run)

    @mcp.tool()
    async def list_cached_symbols() -> dict:
        """List stock symbols that already have OHLCV data in the local SQLite cache.

        Returns:
            `{"ok": true, "symbols": [str, ...]}`.
        """
        return await anyio.to_thread.run_sync(
            lambda: {"ok": True, "symbols": data_service.list_symbols()}
        )
