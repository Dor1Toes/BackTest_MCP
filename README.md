# BackTest_MCP

股票回测引擎 MCP 服务器（QuantForge MCP）：面向 Cursor/Agent 的量化回测与数据服务。
支持通过 MCP tools 执行“动态策略代码校验 → 拉取/缓存行情 → 子进程回测 → 产物/报告生成 → 结果查询”全流程。

**主要技术栈**：Python 3.10+、`mcp`（FastMCP，stdio/SSE）、SQLite（任务/行情/产物索引）、pandas/numpy（数据与指标计算）、akshare/yfinance（行情源，按 A 股/美股路由）、uvx/pyproject（可打包分发）、uvicorn（SSE 托管兼容）。

## 参考说明

本项目核心回测引擎代码参考自开源仓库 [theNeuralHorizon/quantforge](https://github.com/theNeuralHorizon/quantforge)。
在此基础上，结合 MCP 场景补充了工具化封装、服务层与运行流程。

## 功能概览

- 提供股票数据拉取/缓存能力（默认 `auto` 美股 + A股，`yfinance` 美股，`akshare` A股）。
- 提供动态策略代码校验与回测执行。
- 提供回测结果查询、工件下载、Markdown 报告生成。
- 暴露策略生成辅助目录（指标/统计/风控/组合函数与策略样例）。
- 支持多 Symbol（多标的）策略回测。
- 后续待开发：ML 能力完善与 Docker 化部署（如 worker/服务端容器化）。

## 文档

- `docs/quantforge_mcp.md`：MCP 服务器层架构与模块说明
- `docs/quantforge_stock.md`：回测/研究库架构与模块说明

## 目录结构

```text
BackTest_MCP/
├─ pyproject.toml            # 打包配置（供 uvx 从 git 运行）
├─ requirements.txt          # Python 依赖（开发/兼容用）
├─ docs/                     # 架构与使用文档
├─ quantforge_mcp/           # MCP 服务包（server、tools、services、db、resources 等）
├─ quantforge_stock/         # 量化计算与策略库
└─ storage/
   ├─ db/                    # SQLite 数据库目录（包含 .db/.db-wal/.db-shm）
   └─ artifacts/             # 回测产物目录（按 job_id 划分）

> 注意：默认情况下，`storage/` 会**相对当前工作目录（cwd）**解析（例如你在 `C:\Users\username` 启动服务，则默认会落到 `C:\Users\username\storage\...`）。
> 如果在 `C:\Windows\System32` 等不可写目录启动，会自动回退到用户目录（如 `%LOCALAPPDATA%\\quantforge-mcp\\...`）。
> 如需固定位置，建议显式设置 `QUANTFORGE_DB_PATH` / `QUANTFORGE_ARTIFACTS_DIR` 为绝对路径。
```

## 环境要求

- Python 3.10+

## 启动服务

### 方式 1：Cursor/Agent 通过 uvx 接入（推荐）

将以下配置加入你的 Cursor MCP 配置（示例仅展示结构，按你的实际路径调整）：

```json
{
  "mcpServers": {
    "quantforge": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Dor1Toes/BackTest_MCP.git@v0.1.0",
        "quantforge-mcp"
      ]
    }
  }
}
```

（还未发布）如果未来发布到 PyPI，可使用以下形式（示例）：

```json
{
  "mcpServers": {
    "quantforge": {
      "command": "uvx",
      "args": ["quantforge-mcp==0.1.0"],
      "env": { "QUANTFORGE_TRANSPORT": "stdio" }
    }
  }
}
```

### 方式 2：本地运行（开发/调试）

先安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

然后启动 stdio：

```bash
python -m quantforge_mcp
```

### 方式 3：SSE

```bash
set QUANTFORGE_TRANSPORT=sse   # Linux/macOS 用 export
set QUANTFORGE_SSE_PORT=8001
python -m quantforge_mcp
```

## MCP 工具列表

### Data

- `get_stock_data(symbol, start, end, interval)`：获取并汇总 OHLCV 数据。
- `list_cached_symbols()`：查看本地缓存股票代码。
- `prefetch_stock_data(symbols, start, end, interval)`：批量预拉取数据。

### Backtest

- `validate_strategy_code(code)`：策略代码 AST 安全校验。
- `validate_backtest_config(config_json)`：回测配置校验。
- `run_backtest_dynamic(code, config_json)`：运行动态策略回测。
- `list_backtest_jobs(limit, status)`：列出 SQLite 中的历史回测 job。
- `get_backtest_result(job_id)`：查询回测结果。
- `generate_backtest_report(job_id, title)`：生成 Markdown 报告。
- `get_backtest_artifacts(job_id, kind)`：获取回测工件。

## 策略示例

下面给出一个接入 MCP 后 Agent 应该生成的 “动量策略”示例策略代码与对应配置：

> 多标的说明：将 `config_json.symbols` 传入多个标的即可；引擎会在每个 bar 对每个 symbol 分别调用一次 `on_bar(symbol, bar, history)`（其中 `history` 为该 symbol 的单标的历史）。

### 示例策略代码（MomentumStrategy）

```python
\"\"\"动量策略：60日收益率动量，正收益做多，负收益平仓。\"\"\"
from dataclasses import dataclass

import pandas as pd

from quantforge_stock.strategies.base import Strategy


@dataclass
class MomentumStrategy(Strategy):
    lookback: int = 60
    threshold: float = 0.0
    allow_short: bool = False
    name: str = \"momentum\"

    def warmup(self) -> int:
        return self.lookback + 1

    def on_bar(self, symbol: str, bar: pd.Series, history: pd.DataFrame) -> list:
        if len(history) < self.lookback + 1:
            return []
        past = history[\"close\"].iloc[-(self.lookback + 1)]
        now = history[\"close\"].iloc[-1]
        ret = now / past - 1.0
        direction = 0
        if ret > self.threshold:
            direction = 1
        elif ret < -self.threshold and self.allow_short:
            direction = -1
        strength = min(1.0, abs(ret) / max(self.threshold + 1e-6, 0.05))
        return [self._signal(bar.name, symbol, direction, strength, self.name)]
```

### 示例配置（config_json）

```json
{
  "name": "ashare_momentum_real",
  "symbols": ["600519"],
  "start": "2025-07-23",
  "end": "2026-07-23",
  "initial_capital": 100000.0,
  "commission": 0.0003,
  "slippage": 0.001
}
```

## MCP 资源列表

- `quantforge://codegen/spec`：策略代码生成规范。
- `quantforge://data/symbol-guide`：symbol 使用指南。
- `quantforge://examples/nvda_dynamic_config`：动态回测配置示例。
- `quantforge://compute/modules`：可用于策略生成的计算模块与函数目录。
- `quantforge://compute/{module}`：查看单个计算模块详情（如 `quantforge://compute/indicators`）。
- `quantforge://strategies/index`：内置策略示例索引。
- `quantforge://strategies/{name}`：单个策略源码与说明（如 `quantforge://strategies/ma_crossover`）。

## 关键环境变量

所有配置项以 `QUANTFORGE_` 为前缀：

- `QUANTFORGE_DB_PATH`（默认 `storage/db/quantforge.db`，相对 cwd）
- `QUANTFORGE_ARTIFACTS_DIR`（默认 `storage/artifacts`，相对 cwd）
- `QUANTFORGE_DATA_SOURCE`（默认 `auto`）
- `QUANTFORGE_AKSHARE_ADJUST`（默认 `qfq`）
- `QUANTFORGE_ALLOW_SYNTHETIC_FALLBACK`（默认 `true`）
- `QUANTFORGE_SANDBOX_TIMEOUT_SEC`（默认 `120`）
- `QUANTFORGE_TRANSPORT`（`stdio` / `sse`，默认 `stdio`）
- `QUANTFORGE_SSE_PORT`（默认 `8001`）

Windows 示例（将数据/产物固定到你的目录）：

```bash
set QUANTFORGE_DB_PATH=C:\Users\24161\storage\db\quantforge.db
set QUANTFORGE_ARTIFACTS_DIR=C:\Users\24161\storage\artifacts
```

## 关于 `quantforge_stock/ml`

`quantforge_stock/ml` 目前处于开发中。

- 默认禁用；若你明确需要启用实验能力，请手动设置 `QUANTFORGE_ENABLE_EXPERIMENTAL_ML=1`。

```bash
set QUANTFORGE_ENABLE_EXPERIMENTAL_ML=1   # Linux/macOS 用 export
```

## 关于 sandbox 执行

动态回测通过 `sandbox/worker/backtest_worker.py` 以**本地子进程**方式运行（非 Docker）。
超时由 `QUANTFORGE_SANDBOX_TIMEOUT_SEC` 控制；首次拉取行情/初始化数据库可能会稍慢。

## 常见问题

- **`ModuleNotFoundError: quantforge_mcp`**  
  当前推荐直接在仓库根目录执行 `python server.py`；若使用模块方式启动，请在父目录执行并保证 `quantforge_mcp` 在 `PYTHONPATH` 中。

- **Cursor 日志提示：`'uvx' 不是内部或外部命令`**  
  说明 Cursor 启动 MCP 的环境里找不到 `uvx`（PATH 未包含）。请将 `mcpServers.quantforge.command` 改成 `uvx.exe` 的**绝对路径**（例如 `C:\\Users\\username\\.local\\bin\\uvx.exe`），或确保 `uvx` 所在目录已加入系统 PATH。

- **`uvx` 从 `C:\\Windows\\System32` 等目录启动时报 `...\\storage\\db` 创建失败**  
  这是因为默认 `storage/` 会相对当前工作目录（cwd）解析，导致尝试在系统目录下创建 `storage/db`。解决方式：
  - 显式设置 `QUANTFORGE_DB_PATH` / `QUANTFORGE_ARTIFACTS_DIR` 为绝对路径
  - 或设置 `QUANTFORGE_STORAGE_ROOT` 指向可写目录（将作为相对路径的基准）

- **更新版本后仍命中旧缓存**  
  使用 `uvx` 时可在参数前追加 `--reinstall` 强制刷新缓存（例如 `["--reinstall", "--from", "...", "quantforge-mcp"]`）。

- **首次回测较慢**  
  首次拉取行情与初始化数据库会有冷启动开销，属于正常现象。
