# BackTest_MCP

股票回测引擎 MCP 服务器（QuantForge MCP）。

## 参考说明

本项目核心回测引擎代码参考自开源仓库 [theNeuralHorizon/quantforge](https://github.com/theNeuralHorizon/quantforge)。
在此基础上，结合 MCP 场景补充了工具化封装、服务层与运行流程。

## 功能概览

- 提供股票数据拉取/缓存能力（默认 `yfinance`）。
- 提供动态策略代码校验与回测执行。
- 提供回测结果查询、工件下载、Markdown 报告生成。
- 暴露策略生成辅助目录（指标/风控/组合函数与策略样例）。

## 目录结构

```text
BackTest_MCP/
├─ server.py                 # MCP 服务入口
├─ config.py                 # 环境变量配置
├─ requirements.txt          # Python 依赖
├─ tools/                    # MCP 工具注册
├─ services/                 # 业务服务层
├─ db/                       # SQLite 与仓储
├─ quantforge_stock/         # 量化计算与策略库
└─ storage/                  # 回测产物与数据库文件
```

## 环境要求

- Python 3.10+
- 可选：Docker（用于沙箱执行回测 worker）

## 安装

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 启动服务

### 方式 1：stdio（默认，推荐给 MCP Client）

```bash
python -m quantforge_mcp
```

### 方式 2：SSE

```bash
set QUANTFORGE_TRANSPORT=sse   # Linux/macOS 用 export
set QUANTFORGE_SSE_PORT=8001
python -m quantforge_mcp
```

## MCP 工具列表

### Catalog

- `list_compute_modules`：列出可用于策略生成的计算模块导出函数（含签名/描述）。
- `list_strategy_examples`：列出内置策略样例文件与类说明。

### Data

- `get_stock_data(symbol, start, end, interval)`：获取并汇总 OHLCV 数据。
- `list_cached_symbols()`：查看本地缓存股票代码。
- `prefetch_stock_data(symbols, start, end, interval)`：批量预拉取数据。

### Backtest

- `validate_strategy_code(code)`：策略代码 AST 安全校验。
- `validate_backtest_config(config_json)`：回测配置校验。
- `run_backtest_dynamic(code, config_json)`：运行动态策略回测。
- `get_backtest_result(job_id)`：查询回测结果。
- `generate_backtest_report(job_id, title)`：生成 Markdown 报告。
- `get_backtest_artifacts(job_id, kind)`：获取回测工件。

## MCP 资源列表

- `quantforge://codegen/spec`：策略代码生成规范。
- `quantforge://data/symbol-guide`：symbol 使用指南。
- `quantforge://examples/nvda_dynamic_config`：动态回测配置示例。

## 关键环境变量

所有配置项以 `QUANTFORGE_` 为前缀：

- `QUANTFORGE_DB_PATH`（默认 `quantforge_mcp/storage/quantforge.db`）
- `QUANTFORGE_ARTIFACTS_DIR`（默认 `quantforge_mcp/storage/artifacts`）
- `QUANTFORGE_DATA_SOURCE`（默认 `yfinance`）
- `QUANTFORGE_ALLOW_SYNTHETIC_FALLBACK`（默认 `true`）
- `QUANTFORGE_DOCKER_ENABLED`（默认 `true`）
- `QUANTFORGE_DOCKER_IMAGE`（默认 `quantforge-worker:latest`）
- `QUANTFORGE_SANDBOX_TIMEOUT_SEC`（默认 `120`）
- `QUANTFORGE_SANDBOX_MEM_LIMIT`（默认 `512m`）
- `QUANTFORGE_SANDBOX_CPU_QUOTA`（默认 `100000`）
- `QUANTFORGE_TRANSPORT`（`stdio` / `sse`，默认 `stdio`）
- `QUANTFORGE_SSE_PORT`（默认 `8001`）

## 关于 `quantforge_stock/ml`

`quantforge_stock/ml` 目前处于开发中，默认禁用。

- 默认导入会抛出 `ImportError`，防止被其他模块误调用。
- 若你明确需要启用实验能力，请手动设置：

```bash
set QUANTFORGE_ENABLE_EXPERIMENTAL_ML=1   # Linux/macOS 用 export
```

## 常见问题

- **`ModuleNotFoundError: quantforge_mcp`**  
  需在 `quantforge_mcp` 目录的上一级执行，或保证该目录名为 `quantforge_mcp` 并在 `PYTHONPATH` 中。

- **首次回测较慢**  
  首次拉取行情与初始化数据库会有冷启动开销，属于正常现象。
