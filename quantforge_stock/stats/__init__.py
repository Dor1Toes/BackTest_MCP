"""Advanced statistical methods: GARCH, cointegration, covariance shrinkage."""
from quantforge_mcp.quantforge_stock.stats.cointegration import (
    engle_granger,
    half_life_of_mean_reversion,
    johansen_trace,
    rolling_cointegration,
)
from quantforge_mcp.quantforge_stock.stats.garch import GARCHParams, garch11_fit, garch11_forecast
from quantforge_mcp.quantforge_stock.stats.regime import (
    detect_structural_breaks,
    markov_switching_returns,
)
from quantforge_mcp.quantforge_stock.stats.shrinkage import (
    constant_correlation_target,
    ledoit_wolf_shrinkage,
    oracle_shrinkage,
    shrunk_covariance,
)

__all__ = [
    "garch11_fit", "garch11_forecast", "GARCHParams",
    "engle_granger", "johansen_trace", "rolling_cointegration",
    "half_life_of_mean_reversion",
    "ledoit_wolf_shrinkage", "constant_correlation_target",
    "oracle_shrinkage", "shrunk_covariance",
    "markov_switching_returns", "detect_structural_breaks",
]