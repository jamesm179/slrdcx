import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import socketio

from config import (
    COINDCX_WEBSOCKET_URL,
    PING_INTERVAL,
    COINDCX_CHANNELS,
    get_symbol_from_channel,
    PRICE_DATA,
    logger,
)

class SinglePairWebSocketClient:
    """WebSocket client for a single trading pair"""

    def __init__(self, api_key: str, secret_key: str, channel: str, symbol: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.channel = channel
        self.symbol = symbol
        self.sio = socketio.AsyncClient()
        self.connected = False
        self.ping_task = None
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Setup WebSocket event handlers for this specific pair"""

        @self.sio.event
        async def connect():
            logger.info(f"🚀 Connected to CoinDCX WebSocket for {self.symbol}!")
            self.connected = True
            await self._join_authenticated_channel()
            await self._join_price_channel()
            if self.ping_task is None:
                self.ping_task = asyncio.create_task(self._ping_task())

        @self.sio.event
        async def disconnect():
            logger.warning(f"❌ Disconnected from CoinDCX WebSocket for {self.symbol}")
            self.connected = False
            if self.ping_task:
                self.ping_task.cancel()
                self.ping_task = None

        @self.sio.on('price-change')
        async def on_price_change(response):
            """Handle price change events for this specific symbol"""
            try:
                current_time = datetime.now()
                # logger.info(f"📊 Price Change for {self.symbol}: {current_time.strftime('%H:%M:%S')}")
                if isinstance(response, dict) and 'data' in response:
                    data_str = response.get('data')
                    if data_str:
                        data = json.loads(data_str)
                        price = data.get('p')
                        timestamp = data.get('T')
                        if price and timestamp:
                            # logger.info(f"✅ {self.symbol}: {price} at {timestamp}")
                            await self._process_price_update(price, timestamp)
                        # else:
                            # logger.warning(f"⚠️ Missing price or timestamp for {self.symbol}: {data}")
                # else:
                    # logger.warning(f"⚠️ Unexpected response format for {self.symbol}: {response}")
            except Exception as e:
                logger.error(f"Error processing price change for {self.symbol}: {e}")

        @self.sio.event
        async def connect_error(data):
            logger.error(f"Connection error for {self.symbol}: {data}")

        @self.sio.event
        async def pong(data):
            logger.debug(f"Received pong for {self.symbol}")

    async def _join_authenticated_channel(self):
        """Join the authenticated channel using HMAC signature"""
        try:
            secret_bytes = bytes(self.secret_key, encoding='utf-8')
            channel_name = "coindcx"
            body = {"channel": channel_name}
            json_body = json.dumps(body, separators=(',', ':'))
            signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()
            await self.sio.emit('join', {
                'channelName': channel_name,
                'authSignature': signature,
                'apiKey': self.api_key
            })
            logger.info(f"✅ {self.symbol}: Joined authenticated channel")
        except Exception as e:
            logger.error(f"Error joining authenticated channel for {self.symbol}: {e}")

    async def _join_price_channel(self):
        """Join the specific price channel for this trading pair"""
        try:
            await self.sio.emit('join', {'channelName': self.channel})
            logger.info(f"✅ {self.symbol}: Joined channel {self.channel}")
        except Exception as e:
            logger.error(f"Error joining price channel for {self.symbol}: {e}")

    async def _ping_task(self):
        """Send periodic ping to keep connection alive"""
        while self.connected:
            try:
                await asyncio.sleep(PING_INTERVAL)
                if self.connected:
                    await self.sio.emit('ping', {'data': f'Ping for {self.symbol}'})
                    logger.debug(f"📡 Sent ping for {self.symbol}")
            except Exception as e:
                logger.error(f"Error sending ping for {self.symbol}: {e}")
                break

    async def _process_price_update(self, price: str, timestamp: int):
        """Process price update for this specific symbol"""
        try:
            price_float = float(price)
            formatted_price = f"${price_float:.4f}"
            PRICE_DATA[self.symbol] = {
                'symbol': self.symbol,
                'current_price': formatted_price,
                'change_24h': 'Live',
                'status': 'Live',
                'last_updated': timestamp
            }
            # logger.info(f"💰 {self.symbol} = {formatted_price} at {timestamp}")
        except Exception as e:
            logger.error(f"Error processing price update for {self.symbol}: {e}")

    async def connect(self):
        """Connect to CoinDCX WebSocket"""
        try:
            logger.info(f"🔌 Connecting {self.symbol} to {COINDCX_WEBSOCKET_URL}...")
            await self.sio.connect(COINDCX_WEBSOCKET_URL, transports='websocket')
        except Exception as e:
            logger.error(f"Failed to connect {self.symbol}: {e}")
            raise

    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.connected:
            await self.sio.disconnect()
            logger.info(f"👋 Disconnected {self.symbol}")

    async def wait(self):
        """Wait for the WebSocket connection"""
        await self.sio.wait()

class MultiPairWebSocketManager:
    """Manager for multiple WebSocket clients - one per trading pair"""

    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.clients: Dict[str, SinglePairWebSocketClient] = {}
        self.tasks: List[asyncio.Task] = []

    def _create_clients(self):
        """Create individual WebSocket clients for each trading pair"""
        for channel in COINDCX_CHANNELS:
            symbol = get_symbol_from_channel(channel)
            client = SinglePairWebSocketClient(
                self.api_key,
                self.secret_key,
                channel,
                symbol
            )
            self.clients[symbol] = client
            logger.info(f"🔧 Created client for {symbol} -> {channel}")

    async def connect_all(self):
        """Connect all WebSocket clients"""
        self._create_clients()
        connect_tasks = [asyncio.create_task(client.connect()) for client in self.clients.values()]
        await asyncio.gather(*connect_tasks)
        logger.info(f"🌐 All {len(self.clients)} WebSocket clients connected!")

    async def disconnect_all(self):
        """Disconnect all WebSocket clients"""
        disconnect_tasks = [asyncio.create_task(client.disconnect()) for client in self.clients.values()]
        await asyncio.gather(*disconnect_tasks)
        logger.info("👋 All WebSocket clients disconnected!")

    async def wait_all(self):
        """Wait for all WebSocket connections"""
        wait_tasks = [asyncio.create_task(client.wait()) for client in self.clients.values()]
        await asyncio.gather(*wait_tasks)
