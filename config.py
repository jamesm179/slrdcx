import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

def load_config():
    """Load configuration from JSON file or create a default one."""
    config_path = Path(__file__).parent / 'trading_config.json'
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        default_config = {
            "metadata": {"version": "2.0.0"},
            "exchange": {"websocket_url": "wss://ws-api.coindcx.com/v1/sub"},
            "websocket": {"timeout": 60, "ping_interval": 10},
            "trading_pairs": {"default_pairs": [
                {"symbol": "BTC/USDT", "channel": "B-BTC_USDT@prices-futures", "enabled": True},
            ]},
            "server": {"host": "0.0.0.0", "port": 8000},
        }
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        return default_config

CONFIG = load_config()

COINDCX_API_KEY = os.getenv("COINDCX_API_KEY", "test_key")
COINDCX_SECRET_KEY = os.getenv("COINDCX_SECRET_KEY", "test_secret")
COINDCX_WEBSOCKET_URL = CONFIG["exchange"]["websocket_url"]
PING_INTERVAL = CONFIG["websocket"]["ping_interval"]
TRADING_PAIRS = [pair["symbol"] for pair in CONFIG["trading_pairs"]["default_pairs"] if pair.get("enabled", True)]
COINDCX_CHANNELS = [pair["channel"] for pair in CONFIG["trading_pairs"]["default_pairs"] if pair.get("enabled", True)]

PRICE_DATA = {symbol: {"symbol": symbol, "current_price": "$0.0000", "status": "Connecting..."} for symbol in TRADING_PAIRS}
ORDER_BOOK_DATA = {"bids": [], "asks": []}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_symbol_from_channel(channel: str) -> str:
    if "@prices-futures" in channel:
        return channel.replace("@prices-futures", "").replace("B-", "").replace("_", "/")
    return channel

def get_channel_from_symbol(symbol: str) -> str:
    return f"B-{symbol.replace('/', '_')}_USDT@prices-futures"
