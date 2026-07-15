"""Event types flowing through the system."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class EventType(str,Enum):
    MARKET = "MARKET"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    FILL = "FILL"

@dataclass(frozen=True)
class Event:
    event_type: EventType
    timestamp: datetime

@dataclass(frozen=True)
class MarketEvent(Event):
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    @classmethod
    def make(cls, timestamp: datetime, symbol: str, open: float, high: float, low: float, close: float, volume: float) -> MarketEvent:
        return cls(event_type=EventType.MARKET, timestamp=timestamp, symbol=symbol, open=open, high=high, low=low, close=close, volume=volume)
    
@dataclass(frozen=True)
class SignalEvent(Event):
    symbol: str
    direction: int # +1 for long, -1 for short, 0 for flat
    strength: float = 1.0 # 0..1 sizing hint
    strategy_id: str = "default"

@dataclass(frozen=True)
class OrderEvent(Event):
    symbol: str
    order_type: str 
    quantity: float
    direction: int
    limit_price: float | None = None

@dataclass(frozen=True)
class FillEvent(Event):
    symbol: str
    quantity: float
    direction: int
    fill_price: float
    commission: float 
    slippage: float = 0.0