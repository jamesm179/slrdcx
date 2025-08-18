import hashlib
import hmac
import json
import logging
import time
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import logger, COINDCX_API_KEY, COINDCX_SECRET_KEY
from models.orders import OrderSide, OrderType, MarginType

class CoinDCXFuturesClient:
    """CoinDCX Futures API client - Live Trading Only"""

    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = "https://api.coindcx.com"
        self.session = requests.Session()
        retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.headers.update({'Content-Type': 'application/json', 'X-AUTH-APIKEY': self.api_key})
        logger.info(f"🚀 CoinDCX Futures Client initialized - LIVE MODE")

    def _generate_signature(self, body: str) -> str:
        return hmac.new(self.secret_key.encode('utf-8'), body.encode(), hashlib.sha256).hexdigest()

    def create_futures_order(self, symbol: str, side: OrderSide, order_type: OrderType, quantity: float, price: Optional[float] = None, leverage: float = 1.0, margin_type: MarginType = MarginType.CROSSED) -> Dict:
        try:
            timestamp = int(round(time.time() * 1000))
            coindcx_order_type = "market_order" if order_type == OrderType.MARKET else "limit_order"
            body_data = {"timestamp": timestamp, "order": {"side": side.value, "pair": symbol, "order_type": coindcx_order_type, "total_quantity": quantity, "leverage": leverage, "notification": "no_notification", "time_in_force": "good_till_cancel", "hidden": False, "post_only": False}}
            if price and order_type == OrderType.LIMIT:
                body_data["order"]["price"] = str(price)
            body = json.dumps(body_data, separators=(',', ':'))
            signature = self._generate_signature(body)
            headers = {'Content-Type': 'application/json', 'X-AUTH-APIKEY': self.api_key, 'X-AUTH-SIGNATURE': signature}
            response = self.session.post("https://api.coindcx.com/exchange/v1/derivatives/futures/orders/create", data=body, headers=headers, timeout=15)
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ... (other methods)
