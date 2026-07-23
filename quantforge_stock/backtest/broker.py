"""SimulatedBroker: executes orders against synthetic / historical market data.

Supports MARKET, LIMIT, STOP, and STOP_LIMIT order types with realistic
intrabar fill logic (bars are treated as a [low, high] price path; we
assume the path hits stops before limits when both trigger in the same bar).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from quantforge_stock.backtest.commission import CommissionModel, FixedBpsCommission
from quantforge_stock.backtest.slippage import FixedBpsSlippage, SlippageModel
from quantforge_stock.core.event import EventType, FillEvent
from quantforge_stock.core.order import Order, OrderSide, OrderStatus, OrderType

def _limit_fill_price(order: Order, bar: dict[str, float]) -> float | None:
    """Return fill price for a LIMIT if triggered this bar, else None"""
    low, high, open = bar["low"], bar["high"], bar["open"]
    if order.side == OrderSide.BUY:
        if low <= order.limit_price:
            # Conservative : if open is below limit, we'd have filled at open;
            # otherwise filled exactly at the limit.
            return min(order.limit_price,open)
        return None
    else:
        # Sell
        if high >= order.limit_price:
            return max(order.limit_price, open)
        return None

def _stop_triggered(order: Order, bar: dict[str, float]) -> float | None:
    low, high, open = bar["low"], bar["high"], bar["open"]
    stop = order.stop_price
    if stop is None:
        return None
    if order.side == OrderSide.BUY:
        if open >= stop:
            return open
        if high >= stop:
            return stop
        return None
    else:
        if open <= stop:
            return open
        if low <= stop:
            return stop
        return None

@dataclass
class SimulatedBroker:
    slippage: SlippageModel = field(default_factory=FixedBpsSlippage)
    commission: CommissionModel = field(default_factory=FixedBpsCommission)
    pending: list[Order] = field(default_factory=list)
    fills: list[FillEvent] = field(default_factory=list)

    def submit(self, order: Order) -> None:
        self.pending.append(order)

    def cancel(self, order_id: str) -> bool:
        for order in self.pending:
            if order.order_id == order_id and order.is_active:
                order.status = OrderStatus.CANCELED
                return True
        return False
    
    def on_bar(self, timestamp: datetime, symbol: str, bar: dict[str, float]) -> list[FillEvent]:
        """Process pending orders for this symbol using the bar."""
        filled_now : list[FillEvent] = []
        still_pending: list[Order] = []
        for order in self.pending:
            if order.symbol != symbol or not order.is_active:
                still_pending.append(order)
                continue

            side = 1 if order.side == OrderSide.BUY else -1
            fill_ref = bar["open"]
            px: float | None = None

            if order.order_type == OrderType.MARKET:
                px = self.slippage.adjust(fill_ref, order.quantity,bar["volume"], side)
            elif order.order_type == OrderType.LIMIT:
                px = _limit_fill_price(order, bar)
            elif order.order_type == OrderType.STOP:
                trigger = _stop_triggered(order,bar)
                if trigger is not None:
                    px = self.slippage.adjust(trigger, order.quantity, bar["volume"],side)
            elif order.order_type == OrderType.STOP_LIMIT:
                trigger = _stop_triggered(order, bar)
                if trigger is not None:
                    px = _limit_fill_price(order, bar)
                    if px is None:
                        order.order_type = OrderType.LIMIT
                        still_pending.append(order)
                        continue
            if px is None:
                still_pending.append(order)
                continue

            qty = order.quantity
            order.fill(qty,px)
            order.status = OrderStatus.FILLED
            comm = self.commission.charge(px,qty)
            fill = FillEvent(
                event_type = EventType.FILL,
                timestamp = timestamp,
                symbol = symbol,
                quantity = qty,
                direction = side,
                fill_price = px,
                commission = comm,
                slippage = abs(px - fill_ref),
            )
            filled_now.append(fill)
            self.fills.append(fill)
        self.pending = still_pending
        return filled_now

            


