from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional, Dict
from pydantic import BaseModel

@dataclass
class Trade:
    """Trade data structure for real trading with SL/TP support"""
    trade_id: str
    symbol: str
    action: str  # 'buy' or 'sell'
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    leverage: float
    entry_time: str
    exit_time: Optional[str]
    pnl: float
    status: str  # 'open' or 'closed'
    stop_loss: float  # Automatic stop loss level
    take_profit: float  # Automatic take profit level
    exit_reason: str  # 'manual', 'stop_loss', 'take_profit'
    order_id: str  # CoinDCX order ID
    order_status: str  # CoinDCX order status

    def to_dict(self) -> Dict:
        """Convert trade to dictionary"""
        return asdict(self)

@dataclass
class RealTradeResult:
    """Result of a real trade execution"""
    success: bool
    message: str
    order_id: Optional[str] = None
    symbol: str = ""
    side: str = ""
    quantity: float = 0.0
    price: float = 0.0
    status: str = ""
    error_code: Optional[str] = None
    error_details: Optional[Dict] = None
    http_status: Optional[int] = None
    api_response: Optional[Dict] = None
    timestamp: str = ""
    retry_count: int = 0

class TradeRequest(BaseModel):
    symbol: str
    action: str  # 'buy' or 'sell'
    quantity: float = 1.0
    leverage: float = 1.0
    usd_amount: Optional[float] = None  # Optional USD amount for auto-calculation

class TradeSettings(BaseModel):
    default_trade_amount: float = 50.0  # Default $50 USD

class ClosePositionRequest(BaseModel):
    trade_id: str
