# BackTest_MCP

股票回测引擎 MCP 服务器（QuantForge MCP）。

## 参考说明

本项目核心回测引擎代码参考自开源仓库 [theNeuralHorizon/quantforge](https://github.com/theNeuralHorizon/quantforge)。
在此基础上，结合 MCP 场景补充了工具化封装、服务层与运行流程。

## 功能概览

- 提供股票数据拉取/缓存能力（默认 `auto` 美股 + A股，`yfinance` 美股，`akshare` A股）。
- 提供动态策略代码校验与回测执行。
- 提供回测结果查询、工件下载、Markdown 报告生成。
- 暴露策略生成辅助目录（指标/统计/风控/组合函数与策略样例）。
- 后续待开发：ML 能力完善与 Docker 化部署（如 worker/服务端容器化）。

## 目录结构

```text
BackTest_MCP/
├─ server.py                 # MCP 服务入口
├─ config.py                 # 环境变量配置
├─ requirements.txt          # Python 依赖
├─ __main__.py               # 可选：python -m 启动入口
├─ tools/                    # MCP 工具注册
├─ services/                 # 业务服务层
├─ db/                       # SQLite 与仓储
├─ schemas/                  # 回测配置模型
├─ codegen/                  # 动态策略 AST 校验/白名单
├─ resources/                # MCP 资源文档（spec、symbol guide 等）
├─ sandbox/                  # 本地子进程 sandbox runner + worker
├─ quantforge_stock/         # 量化计算与策略库
└─ storage/
   ├─ db/                    # SQLite 数据库目录（包含 .db/.db-wal/.db-shm）
   └─ artifacts/             # 回测产物目录（按 job_id 划分）
```

## 环境要求

- Python 3.10+

## 安装

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 启动服务

### 方式 1：stdio（默认，推荐给 MCP Client）

```bash
python server.py
```

### Cursor MCP 接入示例（mcpServers）

将以下配置加入你的 Cursor MCP 配置（示例仅展示结构，按你的实际路径调整）：

```json
{
  "mcpServers": {
    "quantforge": {
      "command": "python",
      "args": ["C:/Users/xxx/Desktop/BackTest_MCP/quantforge_mcp/server.py"]
    }
  }
}
```

### 方式 2：SSE

```bash
set QUANTFORGE_TRANSPORT=sse   # Linux/macOS 用 export
set QUANTFORGE_SSE_PORT=8001
python server.py
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

- `QUANTFORGE_DB_PATH`（默认 `storage/db/quantforge.db`）
- `QUANTFORGE_ARTIFACTS_DIR`（默认 `storage/artifacts`）
- `QUANTFORGE_DATA_SOURCE`（默认 `auto`）
- `QUANTFORGE_AKSHARE_ADJUST`（默认 `qfq`）
- `QUANTFORGE_ALLOW_SYNTHETIC_FALLBACK`（默认 `true`）
- `QUANTFORGE_SANDBOX_TIMEOUT_SEC`（默认 `120`）
- `QUANTFORGE_TRANSPORT`（`stdio` / `sse`，默认 `stdio`）
- `QUANTFORGE_SSE_PORT`（默认 `8001`）

## 关于 `quantforge_stock/ml`

`quantforge_stock/ml` 目前处于开发中。

- 若你明确需要禁用用实验能力，请手动设置 `QUANTFORGE_ENABLE_EXPERIMENTAL_ML` = `0` 

```bash
set QUANTFORGE_ENABLE_EXPERIMENTAL_ML=1   # Linux/macOS 用 export
```

## 关于 sandbox 执行

动态回测通过 `sandbox/worker/backtest_worker.py` 以**本地子进程**方式运行（非 Docker）。
超时由 `QUANTFORGE_SANDBOX_TIMEOUT_SEC` 控制；首次拉取行情/初始化数据库可能会稍慢。

## 常见问题

- **`ModuleNotFoundError: quantforge_mcp`**  
  当前推荐直接在仓库根目录执行 `python server.py`；若使用模块方式启动，请在父目录执行并保证 `quantforge_mcp` 在 `PYTHONPATH` 中。

- **首次回测较慢**  
  首次拉取行情与初始化数据库会有冷启动开销，属于正常现象。
