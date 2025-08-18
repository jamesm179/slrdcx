import csv
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import logger, PRICE_DATA
from models.trades import Trade
from services.coindcx_client import CoinDCXFuturesClient

class TradeManager:
    """Manages trading operations."""
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.trades_file = self.data_dir / "trades.csv"
        self.open_positions: Dict[str, Trade] = {}
        self.closed_trades: List[Trade] = []
        self.data_dir.mkdir(exist_ok=True)
        self._initialize_csv()
        self._load_existing_data()
        logger.info(f"📊 TradeManager initialized with {len(self.open_positions)} open positions.")

    def _initialize_csv(self):
        if not self.trades_file.exists():
            headers = list(Trade.__annotations__.keys())
            with open(self.trades_file, 'w', newline='', encoding='utf-8') as file:
                csv.writer(file).writerow(headers)

    def _load_existing_data(self):
        if not self.trades_file.exists(): return
        try:
            with open(self.trades_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    trade_data = {k: v for k, v in row.items() if k and v}
                    for f in ['entry_price', 'exit_price', 'quantity', 'leverage', 'pnl', 'stop_loss', 'take_profit']:
                        if f in trade_data:
                            try:
                                trade_data[f] = float(trade_data[f])
                            except (ValueError, TypeError):
                                trade_data[f] = None
                    trade = Trade(**trade_data)
                    if trade.status == 'open':
                        self.open_positions[trade.trade_id] = trade
                    else:
                        self.closed_trades.append(trade)
        except Exception as e:
            logger.error(f"Error loading trade data: {e}")

    def place_trade(self, client: CoinDCXFuturesClient, symbol: str, side: str, quantity: float, leverage: float) -> Dict:
        from models.orders import OrderSide, OrderType
        pair = f"B-{symbol.replace('/', '_')}_USDT"
        order_side = OrderSide.BUY if side == 'buy' else OrderSide.SELL
        order_type = OrderType.MARKET

        result = client.create_futures_order(
            symbol=pair, side=order_side, order_type=order_type,
            quantity=quantity, leverage=leverage
        )
        if result.get("success"):
            order_data = result['data']['orders'][0]
            trade = Trade(
                trade_id=f"trade_{order_data['id']}",
                symbol=symbol, action=side, entry_price=float(order_data['avg_price']),
                quantity=quantity, leverage=leverage, entry_time=datetime.now().isoformat(),
                status='open', order_id=order_data['id'], exit_price=None, exit_time=None, pnl=0.0,
                stop_loss=None, take_profit=None, exit_reason=None, order_status='filled'
            )
            self.open_positions[trade.trade_id] = trade
            self._save_trade_to_csv(trade)
            return {"success": True, "trade": trade}
        else:
            return {"success": False, "error": result.get("error")}

    def _save_trade_to_csv(self, trade: Trade):
        # ... (implementation from before)
        pass

    def get_open_positions_with_pnl(self) -> List[Dict]:
        # ... (implementation from before)
        pass

    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        # ... (implementation from before)
        pass
