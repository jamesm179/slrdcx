import csv
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import (
    logger,
    get_risk_management_config,
    calculate_tp_sl,
    PRICE_DATA,
)
from models.trades import Trade
from services.coindcx_client import CoinDCXFuturesClient
from config import COINDCX_API_KEY, COINDCX_SECRET_KEY

class TradeManager:
    """Manages real trading operations only"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.trades_file = self.data_dir / "trades.csv"
        self.open_positions: Dict[str, Trade] = {}
        self.closed_trades: List[Trade] = []
        self.data_dir.mkdir(exist_ok=True)
        self._initialize_csv()
        self._load_existing_data()
        logger.info(f"📊 TradeManager initialized - LIVE MODE, Positions: {len(self.open_positions)}")

    def _initialize_csv(self):
        if not self.trades_file.exists():
            headers = [
                'trade_id', 'symbol', 'action', 'entry_price', 'exit_price',
                'quantity', 'leverage', 'entry_time', 'exit_time', 'pnl',
                'status', 'stop_loss', 'take_profit', 'exit_reason',
                'order_id', 'order_status'
            ]
            with open(self.trades_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(headers)

    def _load_existing_data(self):
        try:
            if self.trades_file.exists() and self.trades_file.stat().st_size > 0:
                with open(self.trades_file, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        # Filter out None keys
                        filtered_row = {k: v for k, v in row.items() if k is not None}
                        trade_data = {k: (v if v else None) for k, v in filtered_row.items()}

                        for f in ['entry_price', 'exit_price', 'quantity', 'leverage', 'pnl', 'stop_loss', 'take_profit']:
                            if f in trade_data and trade_data[f] is not None:
                                try:
                                    trade_data[f] = float(trade_data[f])
                                except (ValueError, TypeError):
                                    trade_data[f] = None

                        trade = Trade(**trade_data)
                        if trade.status == 'open':
                            self.open_positions[trade.trade_id] = trade
                        else:
                            self.closed_trades.append(trade)
            logger.info(f"📚 Loaded {len(self.open_positions)} open positions and {len(self.closed_trades)} closed trades")
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")

    def place_trade(self, client: CoinDCXFuturesClient, symbol: str, side: str, quantity: float, leverage: float) -> Dict:
        pair = f"B-{symbol.replace('/', '_')}_USDT"
        from models.orders import OrderSide, OrderType
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
                symbol=symbol,
                action=side,
                entry_price=float(order_data['avg_price']),
                quantity=quantity,
                leverage=leverage,
                entry_time=datetime.now().isoformat(),
                order_id=order_data['id'],
                status='open',
                exit_price=None,
                exit_time=None,
                pnl=0.0,
                stop_loss=None,
                take_profit=None,
                exit_reason=None,
                order_status='filled'
            )
            self.open_positions[trade.trade_id] = trade
            self._save_trade_to_csv(trade)
            return {"success": True, "trade": trade}
        else:
            return {"success": False, "error": result.get("error")}

    def _save_trade_to_csv(self, trade: Trade):
        try:
            fieldnames = [
                'trade_id', 'symbol', 'action', 'entry_price', 'exit_price',
                'quantity', 'leverage', 'entry_time', 'exit_time', 'pnl',
                'status', 'stop_loss', 'take_profit', 'exit_reason',
                'order_id', 'order_status'
            ]
            with open(self.trades_file, 'a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                if file.tell() == 0:
                    writer.writeheader()
                writer.writerow(asdict(trade))
        except Exception as e:
            logger.error(f"Error saving trade to CSV: {e}")

    def get_open_positions(self) -> List[Dict]:
        return [t.to_dict() for t in self.open_positions.values()]

    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        return [t.to_dict() for t in sorted(self.closed_trades, key=lambda x: x.entry_time, reverse=True)[:limit]]
