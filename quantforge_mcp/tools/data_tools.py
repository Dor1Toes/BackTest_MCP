from __future__ import annotations

import anyio.to_thread

from quantforge_mcp.services._formatters import summarize_ohlcv
from quantforge_mcp.services.data_service import DataService


def register_data_tools(mcp, data_service: DataService) -> None:
    @mcp.tool()
    async def get_stock_data(symbol: str, start: str = "", end: str = "", interval: str = "1d") -> dict:
        def _run() -> dict:
            frame, source = data_service.get_ohlcv(symbol=symbol, start=start, end=end, interval=interval)
            start_d, end_d = data_service.default_dates(start, end)
            summary = summarize_ohlcv(frame, symbol=symbol, start=start_d, end=end_d)
            return {
                "ok": True,
                "symbol": symbol,
                "start": start_d,
                "end": end_d,
                "rows": summary.rows,
                "source": source,
                "stats": summary.stats,
                "preview_head": [x.model_dump() for x in summary.head],
                "preview_tail": [x.model_dump() for x in summary.tail],
                "missing_pct": summary.missing_pct,
            }

        return await anyio.to_thread.run_sync(_run)

    @mcp.tool()
    async def list_cached_symbols() -> dict:
        return await anyio.to_thread.run_sync(
            lambda: {"ok": True, "symbols": data_service.list_symbols()}
        )

    @mcp.tool()
    async def prefetch_stock_data(symbols: list[str], start: str, end: str, interval: str = "1d") -> dict:
        def _run() -> dict:
            result = []
            for symbol in symbols:
                frame, source = data_service.get_ohlcv(symbol=symbol, start=start, end=end, interval=interval)
                result.append({"symbol": symbol, "rows": len(frame), "source": source})
            return {"ok": True, "items": result}

        return await anyio.to_thread.run_sync(_run)
