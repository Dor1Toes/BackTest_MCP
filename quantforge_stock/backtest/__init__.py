"""Event-driven backtest engine."""
from quantforge_stock.backtest.broker import SimulatedBroker
from quantforge_stock.backtest.commission import (
    CommissionModel,
    FixedBpsCommission,
    NoCommission,
    PerShareCommission,
)
from quantforge_stock.backtest.engine import BacktestEngine, BacktestResult
from quantforge_stock.backtest.slippage import (
    FixedBpsSlippage,
    NoSlippage,
    SlippageModel,
    VolumeImpactSlippage,
)
from quantforge_stock.backtest.tca import TCAReport, analyze_trades

__all__ = [
    "SlippageModel",
    "FixedBpsSlippage",
    "VolumeImpactSlippage",
    "NoSlippage",
    "CommissionModel",
    "FixedBpsCommission",
    "PerShareCommission",
    "NoCommission",
    "SimulatedBroker",
    "BacktestEngine",
    "BacktestResult",
    "TCAReport",
    "analyze_trades",
]