from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class OrderType(Enum):
    """Futures order types based on CoinDCX API"""
    MARKET = "market_order"
    LIMIT = "limit_order"
    STOP_LIMIT = "stop_limit_order"
    TAKE_PROFIT = "take_profit_limit"
    STOP_LOSS = "stop_loss_limit"

class OrderSide(Enum):
    """Order sides"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """Order status based on CoinDCX API"""
    INIT = "init"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    PARTIALLY_CANCELLED = "partially_cancelled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    UNTRIGGERED = "untriggered"

class MarginType(Enum):
    """Margin types"""
    ISOLATED = "isolated"
    CROSSED = "crossed"

@dataclass
class FuturesPosition:
    """Futures position data structure"""
    id: str
    pair: str
    active_pos: float
    inactive_pos_buy: float
    inactive_pos_sell: float
    avg_price: float
    liquidation_price: float
    locked_margin: float
    locked_user_margin: float
    locked_order_margin: float
    take_profit_trigger: Optional[float]
    stop_loss_trigger: Optional[float]
    leverage: float
    mark_price: float
    maintenance_margin: float
    margin_type: str
    margin_currency_short_name: str
    settlement_currency_avg_price: float
    updated_at: int

@dataclass
class FuturesOrder:
    """Futures order data structure"""
    id: str
    pair: str
    side: str
    status: str
    order_type: str
    leverage: float
    price: float
    stop_price: Optional[float]
    avg_price: float
    total_quantity: float
    remaining_quantity: float
    cancelled_quantity: float
    fee_amount: float
    created_at: int
    updated_at: int
    take_profit_price: Optional[float]
    stop_loss_price: Optional[float]

class FuturesAPIError(Exception):
    """Custom exception for Futures API errors"""
    def __init__(self, message: str, error_code: str = None, status_code: int = None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)

class FuturesOrderRequest(BaseModel):
    symbol: str = "XRP"
    action: str = "buy"
    quantity: float = 0.01
    price: Optional[float] = None
    leverage: float = 10.0
    order_type: str = "limit"
