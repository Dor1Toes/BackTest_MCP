from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from quantforge_mcp.config import MCPSettings


def _read_worker_payload(job_dir: Path) -> dict | None:
    """Fallback when subprocess times out but worker already wrote result files."""
    equity_path = job_dir / "equity_curve.csv"
    trades_path = job_dir / "trades.csv"
    config_path = job_dir / "config.json"
    if not equity_path.exists() or not config_path.exists():
        return None
    import pandas as pd

    from quantforge_stock.analytics.performance import summary_stats

    config = json.loads(config_path.read_text(encoding="utf-8"))
    equity = pd.read_csv(equity_path, index_col=0, parse_dates=True).iloc[:, 0]
    trades = pd.read_csv(trades_path) if trades_path.exists() else pd.DataFrame()
    stats = summary_stats(equity, trades=trades if not trades.empty else None)
    symbols = config.get("symbols", [])
    return {
        "symbols": symbols,
        "metrics": {
            "total_return": stats.get("total_return"),
            "annual_return": stats.get("annual_return"),
            "sharpe_ratio": stats.get("sharpe"),
            "sortino_ratio": stats.get("sortino"),
            "max_drawdown": stats.get("max_drawdown"),
            "calmar_ratio": stats.get("calmar"),
            "win_rate": stats.get("win_rate"),
            "n_trades": int(len(trades)),
            "initial_capital": float(config.get("initial_capital", 100000.0)),
            "final_equity": float(equity.iloc[-1]) if len(equity) else float(config.get("initial_capital", 100000.0)),
        },
        "equity_curve_path": str(equity_path),
        "trades_path": str(trades_path),
    }


def run_backtest_in_sandbox(
    *,
    settings: MCPSettings,
    workspace_root: Path,
    job_id: str,
    code: str,
    config: dict,
) -> dict:
    job_dir = settings.artifacts_abspath() / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    strategy_path = job_dir / "strategy.py"
    config_path = job_dir / "config.json"
    strategy_path.write_text(code, encoding="utf-8")
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

    worker_script = workspace_root / "sandbox" / "worker" / "backtest_worker.py"
    cmd = [
        sys.executable,
        str(worker_script),
        "--db",
        str(settings.db_abspath()),
        "--job-dir",
        str(job_dir),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.sandbox_timeout_sec,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        (job_dir / "stdout.txt").write_text(exc.stdout or "", encoding="utf-8")
        (job_dir / "stderr.txt").write_text(exc.stderr or "", encoding="utf-8")
        payload = _read_worker_payload(job_dir)
        if payload is not None:
            return payload
        raise RuntimeError(
            f"sandbox worker timed out after {settings.sandbox_timeout_sec}s "
            "(possible MCP/subprocess or SQLite lock contention; retry once data is cached)"
        ) from exc

    (job_dir / "stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
    (job_dir / "stderr.txt").write_text(proc.stderr or "", encoding="utf-8")

    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "sandbox worker failed")

    lines = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
    if not lines:
        payload = _read_worker_payload(job_dir)
        if payload is not None:
            return payload
        raise RuntimeError("sandbox worker returned empty output")
    return json.loads(lines[-1])
