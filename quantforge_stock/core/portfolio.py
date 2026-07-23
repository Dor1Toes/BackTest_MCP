"""Portfolio aggregates positions, tracks cash and equity."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

from quantforge_stock.core.position import Position

@dataclass
class Portfolio:
    initial_capital: float = 100_000.0
    cash: float = field(init = False)
    positions: dict[str, Position] = field(default_factory=dict)
    equity_curve: list[tuple[datetime, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.cash = self.initial_capital
    
    def position(self, symbol: str) -> Position:
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)
        return self.positions[symbol]
    
    def apply_fill(self, symbol: str, qty: float, price: float, commission: float = 0.0) -> None:
        pos = self.position(symbol)
        cash_delta = pos.apply_fill(qty, price, commission)
        self.cash += cash_delta
    
    def mark_to_market(self, prices:Mapping[str, float])-> None:
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].mark_to_market(price)
    
    @property
    def market_value(self) -> float:
        return sum(position.market_value for position in self.positions.values())
    
    @property
    def equity(self) -> float:
        return self.cash + self.market_value
    
    @property
    def gross_exposure(self) -> float:
        return sum(abs(position.market_value) for position in self.positions.values())
    
    @property
    def net_exposure(self) -> float:
        return self.market_value

    @property
    def leverage(self) -> float:
        equity = self.equity
        return self.gross_exposure / equity if equity > 0 else 0.0
    
    def record_equity(self, timestamp: datetime) -> None:
        self.equity_curve.append((timestamp, self.equity))
    
    def weights(self) -> dict[str, float]:
        equity = self.equity
        if equity <= 0:
            return{}
        return {symbol: position.market_value / equity for symbol, position in self.positions.items()}
    
    def snapshot(self) -> dict:
        return {
            "cash": self.cash,
            "equity": self.equity,
            "market_value": self.market_value,
            "leverage": self.leverage,
            "positions": {
                symbol: {
                    "quantity": position.quantity,
                    "avg_cost": position.avg_cost,
                    "market_value": position.market_value,
                    "unrealized_pnl": position.unrealized_pnl
                }
                for symbol, position in self.positions.items()
            },
        }