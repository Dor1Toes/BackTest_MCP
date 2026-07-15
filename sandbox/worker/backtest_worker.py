from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quantforge_mcp.quantforge_stock.analytics.performance import summary_stats
from quantforge_mcp.quantforge_stock.backtest.broker import SimulatedBroker
from quantforge_mcp.quantforge_stock.backtest.commission import FixedBpsCommission
from quantforge_mcp.quantforge_stock.backtest.engine import BacktestEngine
from quantforge_mcp.quantforge_stock.backtest.slippage import FixedBpsSlippage
from quantforge_mcp.quantforge_stock.strategies.base import Strategy


def _load_strategy(strategy_path: Path) -> Strategy:
    spec = importlib.util.spec_from_file_location("dynamic_strategy", strategy_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to create module spec")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    candidates = []
    for obj in mod.__dict__.values():
        if isinstance(obj, type) and issubclass(obj, Strategy) and obj is not Strategy:
            candidates.append(obj)
    if len(candidates) != 1:
        raise RuntimeError("dynamic strategy must contain exactly one Strategy subclass")
    return candidates[0]()


def _load_data(db_path: Path, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    sql = """
    SELECT date, open, high, low, close, volume
    FROM ohlcv
    WHERE symbol = ? AND interval = ? AND date BETWEEN ? AND ?
    ORDER BY date
    """
    frame = pd.read_sql_query(sql, conn, params=(symbol, interval, start, end))
    conn.close()
    if frame.empty:
        raise RuntimeError("no cached data available for requested symbol/range")
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.set_index("date")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--job-dir", required=True)
    args = parser.parse_args()

    job_dir = Path(args.job_dir)
    config = json.loads((job_dir / "config.json").read_text(encoding="utf-8"))

    strategy = _load_strategy(job_dir / "strategy.py")
    symbol = config["symbols"][0]
    frame = _load_data(Path(args.db), symbol, config["start"], config["end"])

    broker = SimulatedBroker(
        commission=FixedBpsCommission(bps=config.get("commission", 0.0003) * 10_000),
        slippage=FixedBpsSlippage(bps=config.get("slippage", 0.001) * 10_000),
    )
    engine = BacktestEngine(
        strategy=strategy,
        data={symbol: frame},
        initial_capital=config.get("initial_capital", 100000.0),
        broker=broker,
        sizing_fraction=0.95,
    )
    result = engine.run()

    equity_path = job_dir / "equity_curve.csv"
    trades_path = job_dir / "trades.csv"
    result.equity_curve.to_csv(equity_path, header=["equity"])
    result.trades.to_csv(trades_path, index=False)

    stats = summary_stats(result.equity_curve, trades=result.trades if not result.trades.empty else None)
    payload = {
        "symbol": symbol,
        "metrics": {
            "total_return": stats.get("total_return"),
            "annual_return": stats.get("annual_return"),
            "sharpe_ratio": stats.get("sharpe"),
            "sortino_ratio": stats.get("sortino"),
            "max_drawdown": stats.get("max_drawdown"),
            "calmar_ratio": stats.get("calmar"),
            "win_rate": stats.get("win_rate"),
            "n_trades": int(len(result.trades)),
            "initial_capital": float(config.get("initial_capital", 100000.0)),
            "final_equity": float(result.equity_curve.iloc[-1]) if len(result.equity_curve) else float(config.get("initial_capital", 100000.0)),
        },
        "equity_curve_path": str(equity_path),
        "trades_path": str(trades_path),
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
