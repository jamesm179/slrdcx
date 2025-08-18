"""
CoinDCX Trading Dashboard - Final Version
Author: Jules
Date: 2025-08-17
Description: A complete, single-file Dash application for real-time CoinDCX futures trading.
This file consolidates all logic for configuration, API communication, WebSocket handling,
and user interface into one place for simplicity.
"""

# ==============================================================================
# 1. IMPORTS
# ==============================================================================
import asyncio
import csv
import hashlib
import hmac
import json
import logging
import os
import threading
import webbrowser
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import requests
import socketio
from dash import dcc, html, dash_table, Input, Output, State, callback
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dataclasses import dataclass, asdict

# ==============================================================================
# 2. CONFIGURATION & LOGGING
# ==============================================================================

# --- Setup basic logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CoinDCX_Dashboard")

# --- Load Configuration from JSON or create default ---
def load_config():
    config_path = Path(__file__).parent / 'trading_config.json'
    try:
        with open(config_path, 'r') as f:
            logger.info(f"Loading configuration from {config_path}")
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"Config file not found or invalid. Creating a default '{config_path}'.")
        default_config = {
            "api_credentials": {
                "key": os.getenv("COINDCX_API_KEY", "YOUR_API_KEY_HERE"),
                "secret": os.getenv("COINDCX_SECRET_KEY", "YOUR_API_SECRET_HERE")
            },
            "trading_pairs": [
                {"symbol": "BTC/USDT", "channel": "B-BTC_USDT", "enabled": True},
                {"symbol": "ETH/USDT", "channel": "B-ETH_USDT", "enabled": True},
                {"symbol": "XRP/USDT", "channel": "B-XRP_USDT", "enabled": True},
            ],
            "server": {"host": "127.0.0.1", "port": 8050, "debug": True},
            "ping_interval": 10
        }
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        return default_config

CONFIG = load_config()

# --- Extract Constants ---
COINDCX_API_KEY = CONFIG["api_credentials"]["key"]
COINDCX_SECRET_KEY = CONFIG["api_credentials"]["secret"]
PING_INTERVAL = CONFIG.get("ping_interval", 10)
TRADING_PAIRS = [pair["symbol"] for pair in CONFIG["trading_pairs"] if pair["enabled"]]
COINDCX_CHANNELS = [f"{pair['channel']}@prices-futures" for pair in CONFIG["trading_pairs"] if pair["enabled"]]

# --- Global Data Stores ---
PRICE_DATA = {
    symbol: {"symbol": symbol, "price": 0.0, "status": "Connecting..."} for symbol in TRADING_PAIRS
}
OPEN_POSITIONS: Dict[str, 'Trade'] = {}
TRADE_HISTORY: List['Trade'] = []


# ==============================================================================
# 3. DATA MODELS
# ==============================================================================

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    MARKET = "market_order"
    LIMIT = "limit_order"

@dataclass
class Trade:
    trade_id: str
    symbol: str
    side: str
    entry_price: float
    quantity: float
    leverage: float
    status: str = 'open'
    entry_time: str = datetime.now().isoformat()
    pnl: float = 0.0

    def to_dict(self):
        return asdict(self)

# ==============================================================================
# 4. API & WEBSOCKET CLIENTS
# ==============================================================================

class CoinDCXClient:
    """Handles communication with the CoinDCX REST API."""
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key.encode('utf-8')
        self.base_url = "https://api.coindcx.com"
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        logger.info("CoinDCX API Client initialized.")

    def _generate_signature(self, body_str: str) -> str:
        return hmac.new(self.secret_key, body_str.encode('utf-8'), hashlib.sha256).hexdigest()

    def place_market_order(self, symbol, side: OrderSide, quantity, leverage):
        try:
            pair = f"B-{symbol.replace('/', '_')}_USDT"
            timestamp = int(time.time() * 1000)
            body = {
                "timestamp": timestamp,
                "order": {
                    "side": side.value,
                    "pair": pair,
                    "order_type": OrderType.MARKET.value,
                    "total_quantity": quantity,
                    "leverage": leverage
                }
            }
            body_str = json.dumps(body, separators=(',', ':'))
            signature = self._generate_signature(body_str)
            headers = {
                'Content-Type': 'application/json',
                'X-AUTH-APIKEY': self.api_key,
                'X-AUTH-SIGNATURE': signature
            }
            response = self.session.post(f"{self.base_url}/exchange/v1/derivatives/futures/orders/create", data=body_str, headers=headers, timeout=10)

            if response.status_code == 200:
                logger.info(f"Successfully placed order: {response.json()}")
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Failed to place order: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"Exception placing order: {e}")
            return {"success": False, "error": str(e)}

class WebSocketManager:
    """Handles real-time data streams from CoinDCX."""
    def __init__(self, api_key, secret_key, channels):
        self.sio = socketio.AsyncClient()
        self.api_key = api_key
        self.secret_key = secret_key.encode('utf-8')
        self.channels = channels
        self.setup_handlers()
        logger.info("WebSocket Manager initialized.")

    def setup_handlers(self):
        @self.sio.event
        async def connect():
            logger.info("WebSocket connected successfully.")
            await self.authenticate_and_join()

        @self.sio.event
        async def disconnect():
            logger.warning("WebSocket disconnected.")

        @self.sio.on('price-change')
        async def on_price_change(data):
            try:
                if 'data' in data:
                    price_data = json.loads(data['data'])
                    symbol = price_data.get('s', '').replace('B-', '').replace('_USDT', '/USDT')
                    if symbol in PRICE_DATA:
                        PRICE_DATA[symbol]['price'] = float(price_data.get('p', 0.0))
                        PRICE_DATA[symbol]['status'] = 'Live'
            except Exception as e:
                logger.error(f"Error processing price change: {e}")

    async def authenticate_and_join(self):
        try:
            body = json.dumps({"channel": "coindcx"}, separators=(',', ':'))
            signature = hmac.new(self.secret_key, body.encode('utf-8'), hashlib.sha256).hexdigest()
            await self.sio.emit('join', {'channelName': "coindcx", 'authSignature': signature, 'apiKey': self.api_key})
            logger.info("Authenticated and joined base channel.")

            for channel in self.channels:
                await self.sio.emit('join', {'channelName': channel})
                logger.info(f"Joined channel: {channel}")
        except Exception as e:
            logger.error(f"Error authenticating/joining channels: {e}")

    async def start(self):
        try:
            await self.sio.connect("wss://ws-api.coindcx.com/v1/sub", transports='websocket')
            await self.sio.wait()
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")

# ==============================================================================
# 5. BUSINESS LOGIC & THREADING
# ==============================================================================

api_client = CoinDCXClient(COINDCX_API_KEY, COINDCX_SECRET_KEY)
ws_manager = WebSocketManager(COINDCX_API_KEY, COINDCX_SECRET_KEY, COINDCX_CHANNELS)

def run_websocket():
    """Target function for the WebSocket thread."""
    logger.info("Starting WebSocket thread...")
    asyncio.run(ws_manager.start())

# Start the websocket manager in a background thread
ws_thread = threading.Thread(target=run_websocket, daemon=True)
ws_thread.start()

# ==============================================================================
# 6. DASH APPLICATION LAYOUT & CALLBACKS
# ==============================================================================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    dcc.Store(id='trade-data-store', data={'positions': [], 'history': []}),
    dcc.Interval(id='interval-component', interval=1000, n_intervals=0),

    html.H1("CoinDCX Scalping Dashboard", className="my-4"),

    dbc.Row([
        # Left Column
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Trade Execution"),
                dbc.CardBody([
                    dcc.Dropdown(id='trade-symbol', options=TRADING_PAIRS, value=TRADING_PAIRS[0], className="mb-2"),
                    dbc.InputGroup([dbc.InputGroupText("Qty"), dbc.Input(id='trade-quantity', type='number', value=1)]),
                    dbc.InputGroup([dbc.InputGroupText("Lev"), dbc.Input(id='trade-leverage', type='number', value=10)], className="mt-2"),
                    dbc.Row([
                        dbc.Col(dbc.Button("Buy / Long", id='buy-button', color="success", className="w-100 mt-3")),
                        dbc.Col(dbc.Button("Sell / Short", id='sell-button', color="danger", className="w-100 mt-3")),
                    ]),
                    html.Div(id='trade-output', className="mt-2")
                ])
            ], className="mb-4"),
        ], md=4),

        # Right Column
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Live Prices"),
                dbc.CardBody(html.Div(id='price-table-live'))
            ])
        ], md=8),
    ]),

    dbc.Row([
        dbc.Col(html.H4("Open Positions", className="mt-4")),
        dbc.Col(html.Div(id='positions-table-live')),
    ])

], fluid=True)

# --- Callbacks ---

@callback(Output('price-table-live', 'children'), Input('interval-component', 'n_intervals'))
def update_price_table(n):
    df = pd.DataFrame(list(PRICE_DATA.values()))
    return dbc.Table.from_dataframe(df, striped=True, bordered=True, hover=True)

@callback(
    Output('positions-table-live', 'children'),
    Output('trade-output', 'children'),
    Input('buy-button', 'n_clicks'),
    Input('sell-button', 'n_clicks'),
    State('trade-symbol', 'value'),
    State('trade-quantity', 'value'),
    State('trade-leverage', 'value'),
    prevent_initial_call=True
)
def handle_trade_and_update_positions(buy_clicks, sell_clicks, symbol, quantity, leverage):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, ""

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    side = OrderSide.BUY if button_id == 'buy-button' else OrderSide.SELL

    if not all([symbol, quantity, leverage]):
        return dash.no_update, dbc.Alert("All trade fields are required.", color="warning")

    # --- Execute Trade ---
    result = api_client.place_market_order(symbol, side, quantity, leverage)

    if result.get("success"):
        order_info = result['data']['orders'][0]
        trade_id = order_info['id']
        entry_price = float(order_info['avg_price'])

        new_trade = Trade(
            trade_id=trade_id,
            symbol=symbol,
            side=side.value,
            entry_price=entry_price,
            quantity=float(quantity),
            leverage=float(leverage)
        )
        OPEN_POSITIONS[trade_id] = new_trade
        alert = dbc.Alert(f"Success: {side.value} order for {quantity} {symbol} placed.", color="success")
    else:
        alert = dbc.Alert(f"Error: {result.get('error')}", color="danger")

    # --- Update Positions Table ---
    positions_df = pd.DataFrame([p.to_dict() for p in OPEN_POSITIONS.values()])
    positions_table = dbc.Table.from_dataframe(positions_df, striped=True, bordered=True, hover=True) if not positions_df.empty else "No open positions."

    return positions_table, alert

# ==============================================================================
# 7. MAIN EXECUTION
# ==============================================================================

if __name__ == '__main__':
    host = CONFIG["server"]["host"]
    port = CONFIG["server"]["port"]
    logger.info(f"Starting Dash server on http://{host}:{port}")
    app.run_server(debug=CONFIG["server"]["debug"], host=host, port=port)
