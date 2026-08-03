from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

APP = Path(__file__).resolve().parent
_REPO_ROOT = APP.parents[3] if len(APP.parents) > 3 and (APP.parents[3] / "pyproject.toml").exists() else APP.parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from quantforge_mcp.codegen import load_backtest_config, load_strategy
from quantforge_stock.analytics.performance import summary_stats
from quantforge_stock.backtest.broker import SimulatedBroker
from quantforge_stock.backtest.commission import FixedBpsCommission
from quantforge_stock.backtest.engine import BacktestEngine
from quantforge_stock.backtest.slippage import FixedBpsSlippage


def _connect_db(db_path: Path) -> "sqlite3.Connection":
    import sqlite3

    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def _load_data(db_path: Path, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    conn = _connect_db(db_path)
    sql = """
    SELECT date, open, high, low, close, volume
    FROM ohlcv
    WHERE symbol = ? AND interval = ? AND date BETWEEN ? AND ?
    ORDER BY date
    """
    frame = pd.read_sql_query(sql, conn, params=(symbol, interval, start, end))
    conn.close()
    if frame.empty:
        raise RuntimeError(f"no cached data available for symbol={symbol}, range={start}..{end}")
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.set_index("date")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--job-dir", required=True)
    args = parser.parse_args()

    job_dir = Path(args.job_dir)
    config = load_backtest_config(source=job_dir / "config.json")

    strategy = load_strategy(source=job_dir / "strategy.py")
    symbols = config.symbols
    data: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        frame = _load_data(Path(args.db), symbol, config.start, config.end)
        data[symbol] = frame

    broker = SimulatedBroker(
        commission=FixedBpsCommission(bps=config.commission * 10_000),
        slippage=FixedBpsSlippage(bps=config.slippage * 10_000),
    )
    engine = BacktestEngine(
        strategy=strategy,
        data=data,
        initial_capital=config.initial_capital,
        broker=broker,
        sizing_fraction=float(config.sizing_fraction),
        target_weights=config.target_weights,
        rebalance=config.rebalance,
        history_tail=config.history_tail,
    )
    result = engine.run()

    equity_path = job_dir / "equity_curve.csv"
    trades_path = job_dir / "trades.csv"
    result.equity_curve.to_csv(equity_path, header=["equity"])
    result.trades.to_csv(trades_path, index=False)

    stats = summary_stats(result.equity_curve, trades=result.trades if not result.trades.empty else None)
    payload = {
        "symbols": symbols,
        "metrics": {
            "total_return": stats.get("total_return"),
            "annual_return": stats.get("annual_return"),
            "sharpe_ratio": stats.get("sharpe"),
            "sortino_ratio": stats.get("sortino"),
            "max_drawdown": stats.get("max_drawdown"),
            "calmar_ratio": stats.get("calmar"),
            "win_rate": stats.get("win_rate"),
            "n_trades": int(len(result.trades)),
            "initial_capital": float(config.initial_capital),
            "final_equity": float(result.equity_curve.iloc[-1]) if len(result.equity_curve) else float(config.initial_capital),
        },
        "equity_curve_path": str(equity_path),
        "trades_path": str(trades_path),
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
