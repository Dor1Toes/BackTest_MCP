## `quantforge_stock` 架构总览（回测/研究库）

`quantforge_stock` 是“量化计算与策略库”，提供：

- **回测引擎**（事件驱动、broker/portfolio/order）
- **指标库**（technical/statistical）
- **数据层**（akshare/yfinance + 合成数据）
- **分析/报告**（performance/tearsheet/benchmark）
- **策略样例**（MA、动量、均值回归、配对、截面等）
- **风险/组合优化/统计**（risk、portfolio、stats）
- **ML（实验）**：开发中...

`quantforge_mcp` 通过 sandbox worker 调用这里的能力，并将结果回传给 MCP Client。

### 模块架构图

```text
quantforge_stock/
├─ backtest/                   # 回测引擎、broker、费用/滑点、TCA
│  ├─ engine.py
│  ├─ broker.py
│  ├─ commission.py
│  ├─ slippage.py
│  ├─ tca.py
│  └─ __init__.py
├─ core/                       # 事件/订单/持仓/组合等核心对象
│  ├─ event.py
│  ├─ order.py
│  ├─ position.py
│  ├─ portfolio.py
│  ├─ constants.py
│  └─ __init__.py
├─ data/                       # 数据加载与合成数据
│  ├─ loader.py
│  ├─ synthetic.py
│  └─ __init__.py
├─ indicators/                 # 技术/统计指标
│  ├─ technical.py
│  ├─ statistical.py
│  └─ __init__.py
├─ analytics/                  # 绩效评估/基准/报告
│  ├─ performance.py
│  ├─ benchmark.py
│  ├─ tearsheet.py
│  ├─ attribution.py
│  └─ __init__.py
├─ strategies/                 # 策略示例与参考实现
│  ├─ base.py
│  ├─ ma_crossover.py
│  ├─ momentum.py
│  ├─ mean_reversion.py
│  ├─ pairs_trading.py
│  ├─ cross_sectional_momentum.py
│  ├─ dual_momentum.py
│  ├─ vol_target.py
│  └─ __init__.py
├─ risk/                       # 风险指标与风险分析工具箱
├─ portfolio/                  # 组合优化工具箱（Markowitz/HRP/BL 等）
├─ stats/                      # 统计工具箱（协整/GARCH/收缩等）
├─ ml/                         # 机器学习模块（开发中）
└─ __init__.py
```

### backtest（回测子系统）

- **`quantforge_stock/backtest/engine.py`**：`BacktestEngine`
  - 多 symbol 的逐 bar 循环（按 `rebalance` 频率触发策略）
  - 每个 symbol 维护历史 buffer，传给策略的 `history` 是**单标的 DataFrame**
  - 仓位 sizing：
    - `target_weights=True`：`strength` 解释为**目标权重**（占净值比例）
    - 否则：按 `sizing_fraction` 与 `strength`（内部 clamp）计算目标仓位
  - `history_tail`：可选，限制策略可见历史窗口
- **`quantforge_stock/backtest/broker.py`**：`SimulatedBroker`
  - 处理订单、滑点、手续费与成交回报
- **`quantforge_stock/backtest/commission.py` / `slippage.py`**：费用与滑点模型
- **`quantforge_stock/backtest/tca.py`**：简单交易成本分析（TCA）

### core（交易与组合基础设施）

- **`core/event.py`**：事件/信号结构（`SignalEvent` 等）
- **`core/order.py`**：订单结构（side/type/qty）
- **`core/portfolio.py`**：组合、持仓、权益曲线记录
- **`core/position.py`**：单标的持仓对象

### indicators（指标）

- **`indicators/technical.py`**：常用技术指标（SMA/EMA/RSI/MACD/Bollinger 等）
- **`indicators/statistical.py`**：统计类指标（rolling_zscore、rolling_beta 等）

### data（数据）

- **`data/loader.py`**：数据加载与归一化
  - A 股 symbol 解析与适配（支持 `600519` / `sh600519` / `600519.SH`）
  - 远端数据源（akshare/yfinance）封装
- **`data/synthetic.py`**：合成 OHLCV（用于数据缺失时回退）

### analytics（绩效/报告）

- **`analytics/performance.py`**：收益率、夏普、回撤等汇总指标（`summary_stats`）
- **`analytics/tearsheet.py`**：Markdown 报告（tearsheet）
- **`analytics/benchmark.py`**：基准相关分析（如 alpha/beta 等）

### strategies（策略样例/参考）

这里的策略文件主要用于：
- 作为内置示例（通过 MCP 资源 `quantforge://strategies/*` 展示）
- 给动态策略写法提供参考（但动态策略 import 受 allowlist 限制）

常见示例：
- `ma_crossover.py`、`momentum.py`、`mean_reversion.py`
- `pairs_trading.py`、`cross_sectional_momentum.py`
- `vol_target.py`：对 signal strength 做波动率缩放的包装器

### risk / portfolio / stats

这三块是“研究/分析工具箱”

- **`risk/`**：风险指标、VaR/CVaR、回撤、压力测试、模拟等
- **`portfolio/`**：均值方差、风险平价、HRP、Black-Litterman 等组合优化
- **`stats/`**：协整、GARCH、收缩估计等统计工具

### ml（实验模块）

- **`quantforge_stock/ml/__init__.py`**：默认禁用；需要 `QUANTFORGE_ENABLE_EXPERIMENTAL_ML=1` 才可导入
- 其余模块（`features/factor_model/forecast/trainer` 等）属于实验能力，不建议默认作为生产依赖路径

## 后续更新计划（Roadmap）

- **完善 ML**
  - 补齐端到端示例（训练 → 预测 → 产生信号 → 回测）
  - 明确数据对齐/特征工程/训练评估流程与复现方式
- **提升回测隔离与可部署性**
  - 与 `quantforge_mcp` 的 Docker worker 对齐，确保在容器环境下可稳定运行
- **稳定 API 边界**
  - 明确“策略可 import 的模块”（allowlist）与“研究分析工具箱”（risk/portfolio/stats）的边界与使用建议

