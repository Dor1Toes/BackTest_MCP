# QuantForge Dynamic Strategy Code Spec

Read before writing strategy code:
- `quantforge://compute/modules` - module/function reference
- `quantforge://strategies/index` - built-in strategy examples
- `quantforge://data/symbol-guide` - symbol formats (A-share / US)

## Class structure

- Include exactly one class inheriting `Strategy`.
- Required methods: `warmup(self) -> int` and `on_bar(self, symbol, bar, history) -> list[SignalEvent]`.
- `bar`: current OHLCV row (`pd.Series`), index name is timestamp.
- `history`: **this symbol only** OHLCV DataFrame (not a multi-symbol panel).
- Return `[]` when no action.

## Allowed imports (enforced by AST validator)

```python
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import ...  # optional

from quantforge_stock.strategies.base import Strategy
from quantforge_stock.core.event import SignalEvent  # optional if using self._signal
from quantforge_stock.indicators.technical import ema, rsi, macd, ...  # pick what you need
from quantforge_stock.indicators.statistical import rolling_zscore, rolling_beta, ...
```

**Not allowed** network, filesystem, subprocess.

## Forbidden calls

`exec`, `eval`, `open`, `__import__`, `compile`

## Signals

Use `Strategy._signal(ts, symbol, direction, strength, strategy_id)`:

| direction | meaning |
|-----------|---------|
| +1 | long / increase long |
| -1 | short / increase short |
| 0 | flat / close position |

| strength | meaning |
|----------|---------|
| 0.0–1.0 | fraction of equity allocated **per signal** (engine uses ~95% sizing cap) |

**Multi-symbol:** split weights so total target exposure stays reasonable, e.g. 4 equal-weight longs → each `strength=0.25`, not four times `1.0`.

For cross-sectional / pairs logic, accumulate per-symbol state in the strategy instance (see `quantforge://strategies/cross_sectional_momentum`).

## Minimal template

```python
from dataclasses import dataclass
import pandas as pd
from quantforge_stock.strategies.base import Strategy
from quantforge_stock.indicators.technical import ema


@dataclass
class MyStrategy(Strategy):
    fast: int = 10
    slow: int = 30
    name: str = "my_strategy"

    def warmup(self) -> int:
        return self.slow + 2

    def on_bar(self, symbol: str, bar: pd.Series, history: pd.DataFrame) -> list:
        close = history["close"]
        if len(close) < self.slow + 2:
            return []
        diff = ema(close, self.fast) - ema(close, self.slow)
        if diff.iloc[-2] <= 0 < diff.iloc[-1]:
            return [self._signal(bar.name, symbol, 1, 1.0, self.name)]
        return []
```

## Backtest config (JSON for `run_backtest_dynamic`)

### Config A: default sizing mode (target_weights disabled)

This is the simplest setup and works well for **single-symbol** strategies.

- `target_weights=false` (default): `strength` in `self._signal(...)` is treated as a **signal strength hint** (0.0–1.0).
- The engine converts it into position sizing using `sizing_fraction` (and clamps strength into a safe range internally).
- `history_tail` is **optional**. If omitted (or set to `null`), strategies will see the full available history.
- `last_rebalance_ts` is **optional** (`YYYY-MM-DD`). Only used by `scan_strategy_signals` when `rebalance` is `weekly` or `monthly`; omit to scan every latest bar regardless of cadence.

```json
{
  "name": "single_symbol_default",
  "symbols": ["NVDA"],
  "start": "2024-01-01",
  "end": "2025-01-01",
  "initial_capital": 100000,
  "commission": 0.0003,
  "slippage": 0.001,
  "target_weights": false,
  "sizing_fraction": 0.95,
  "rebalance": "bar",
  "history_tail": 252
}
```

### Config B: target-weight mode (target_weights enabled)

When `target_weights=true`, `strength` in `self._signal(...)` must be the **target weight** (0.0–1.0) for that symbol (i.e. portfolio weight), not a “signal confidence”.

For multi-symbol strategies, you should **normalize weights** so total exposure stays reasonable (e.g. 4 equal-weight longs → each `strength=0.25`).
`history_tail` is **optional**. If omitted (or set to `null`), strategies will see the full available history.

```json
{
  "name": "multi_symbol_weighted",
  "symbols": ["600519", "000001"],
  "start": "2024-01-01",
  "end": "2024-12-31",
  "initial_capital": 100000,
  "commission": 0.0003,
  "slippage": 0.001,
  "target_weights": true,
  "rebalance": "bar",
  "history_tail": 252
}
```

## Workflow

1. Read references:
   - `quantforge://codegen/spec`
   - `quantforge://compute/modules`
   - `quantforge://strategies/index` and one relevant `quantforge://strategies/{name}`
2. Write strategy code (exactly one `Strategy` subclass) and prepare backtest `config_json` (`symbols`, `start`, `end`, capital, costs).
3. `get_stock_data(symbols, start, end, preview=False)` when cache is empty or stale.
4. `run_backtest_dynamic(code, config_json)` — strategy code and config are validated automatically before execution.
5. (Optional) `list_backtest_jobs(limit, status)` to list recent jobs (useful if you lost the `job_id`).
6. `get_backtest_result(job_id)` to inspect status/metrics.
7. (Optional) `generate_backtest_report(job_id, title)` to generate a Markdown report.
8. (Optional) `get_backtest_artifacts(job_id, kind)` to download artifacts (e.g. `equity_curve`, `trades`, `stdout`, `stderr`, `report_markdown`).
9. (Optional) `scan_strategy_signals(job_id, ...)` to scan the latest bar for signals on a saved strategy.

