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

```json
{
  "name": "my_strategy",
  "symbols": ["600519", "000001"],
  "start": "2024-01-01",
  "end": "2024-12-31",
  "initial_capital": 100000,
  "commission": 0.0003,
  "slippage": 0.001
}
```

## Workflow

1. Read references:
   - `quantforge://codegen/spec`
   - `quantforge://compute/modules`
   - `quantforge://strategies/index` and one relevant `quantforge://strategies/{name}`
2. Write strategy code (exactly one `Strategy` subclass) and prepare backtest `config_json` (`symbols`, `start`, `end`, capital, costs).
3. `validate_strategy_code(code)` and fix all validation errors until `valid=true`.
4. `validate_backtest_config(config_json)` and fix config errors/warnings.
5. `prefetch_stock_data(symbols, start, end)` when cache is empty or stale.
6. `run_backtest_dynamic(code, config_json)` to start the backtest job.
7. (Optional) `list_backtest_jobs(limit, status)` to list recent jobs (useful if you lost the `job_id`).
8. `get_backtest_result(job_id)` to inspect status/metrics.
9. (Optional) `generate_backtest_report(job_id, title)` to generate a Markdown report.
10. (Optional) `get_backtest_artifacts(job_id, kind)` to download artifacts (e.g. `equity_curve`, `trades`, `stdout`, `stderr`, `report_markdown`).

