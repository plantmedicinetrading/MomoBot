# app/trading/stream/polygon_stream.py

import os
import asyncio
import logging
import websockets
import json
import traceback
import requests
from datetime import datetime, timedelta

from ...state import config
from ..core.breakout_logic import process_quote_for_breakout
from ..core.trade_update import handle_trade_update
from ..core.candle_builder import handle_new_quote, handle_new_quote_10s

logger = logging.getLogger(__name__)

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
POLYGON_WS_URL = "wss://socket.polygon.io/stocks"

def fetch_historical_aggregated_bars(symbol, timeframe='1m', limit=500, to=None):
    """
    Fetch historical aggregated bars from Polygon REST API.
    timeframe: '1m', '5m', or '10s' (10s will be synthesized from 1m if not available)
    limit: number of bars
    to: end datetime (UTC, ISO string or datetime), default now
    Returns: list of dicts [{time, open, high, low, close, volume}]
    """
    api_key = POLYGON_API_KEY
    if not api_key:
        raise ValueError('POLYGON_API_KEY not set')
    if to is None:
        to_dt = datetime.utcnow()
    elif isinstance(to, str):
        to_dt = datetime.fromisoformat(to)
    else:
        to_dt = to
    # Clamp to_dt to no later than yesterday's market close (Polygon won't have future data)
    market_close_dt = datetime.utcnow()
    if datetime.utcnow().hour < 20:  # before 8pm UTC, use previous day (market close is 8pm UTC)
        market_close_dt = datetime.utcnow() - timedelta(days=1)
    if to_dt > market_close_dt:
        to_dt = market_close_dt
    multiplier = 1
    timespan = 'minute'
    if timeframe == '5m':
        multiplier = 5
    elif timeframe == '1m':
        multiplier = 1
    elif timeframe == '10s':
        # Polygon does not provide 10s bars, so we will fetch 1m and split client-side if needed
        multiplier = 1
    else:
        raise ValueError('Unsupported timeframe')
    # Calculate from date
    total_minutes = limit * (5 if timeframe == '5m' else 1)
    from_dt = to_dt - timedelta(minutes=total_minutes)
    # Clamp from_dt to not be in the future
    if from_dt > market_close_dt:
        from_dt = market_close_dt - timedelta(minutes=total_minutes)
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol.upper()}/range/{multiplier}/{timespan}/{from_dt.date()}T{from_dt.time().strftime('%H:%M:%S')}/{to_dt.date()}T{to_dt.time().strftime('%H:%M:%S')}?adjusted=true&sort=asc&limit={limit}&apiKey={api_key}"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    bars = []
    for bar in data.get('results', []):
        bars.append({
            'time': int(bar['t'] // 1000),
            'open': bar['o'],
            'high': bar['h'],
            'low': bar['l'],
            'close': bar['c'],
            'volume': bar['v']
        })
    return bars

class PolygonStream:
    def __init__(self):
        self.ws = None
        self._quote_handlers = {}
        self._active_symbol = None
        self._socketio = None
        self._connected = False
        self._subscribed_symbols = set()
        self.event_loop = None  # Store the event loop used for async scheduling

    def set_socketio(self, socketio):
        self._socketio = socketio

    async def subscribe_to_ticker(self, symbol):
        logger.info(f"[Polygon] subscribe_to_ticker called for {symbol}")
        logger.info(f"[Polygon] self._connected={self._connected}, self.ws={self.ws}")
        self._active_symbol = symbol
        if self.ws and self._connected:
            sub_msg = json.dumps({"action": "subscribe", "params": f"T.{symbol},Q.{symbol}"})
            logger.info(f"[Polygon] Sending subscription message: {sub_msg}")
            await self.ws.send(sub_msg)
            logger.info(f"[Polygon] Subscribed to {symbol} (trades & quotes)")
            self._subscribed_symbols.add(symbol)
        else:
            logger.warning(f"[Polygon] WebSocket not connected. Cannot subscribe to {symbol} yet.")

    async def _quote_handler(self, symbol, event):
        # Only quote events should be passed to candle-building functions
        from datetime import datetime, timezone
        from ...socketio_events import emit_price_update
        class SimpleQuote:
            def __init__(self, symbol, ask_price, bid_price, ask_size, bid_size, timestamp):
                self.symbol = symbol
                self.ask_price = ask_price
                self.bid_price = bid_price
                self.ask_size = ask_size
                self.bid_size = bid_size
                self.timestamp = timestamp
        ts = datetime.fromtimestamp(event["t"] / 1000, tz=timezone.utc)
        ask_price = event.get("ap")
        bid_price = event.get("bp")
        ask_size = event.get("as", 0)
        bid_size = event.get("bs", 0)
        quote = SimpleQuote(
            symbol=symbol,
            ask_price=ask_price,
            bid_price=bid_price,
            ask_size=ask_size,
            bid_size=bid_size,
            timestamp=ts
        )
        # Update last_quote in state before any candle or breakout logic
        from ...shared_state import ticker_states
        if symbol not in ticker_states:
            ticker_states[symbol] = {}
        ticker_states[symbol]["last_quote"] = quote
        # Emit price update to frontend
        emit_price_update(
            symbol,
            quote.ask_price,
            quote.bid_price,
            quote.ask_size,
            quote.bid_size,
            quote.timestamp
        )
        # Tick-level breakout and trade target checks
        from ..core.breakout_logic import process_quote_for_breakout
        process_quote_for_breakout(symbol, quote)
        handle_new_quote(symbol, quote)
        handle_new_quote_10s(symbol, quote)
        from ..core.candle_builder import handle_new_quote_5m
        handle_new_quote_5m(symbol, quote)
        # Do not call candle-building functions for trade events!

    async def _trade_handler(self, symbol, event):
        # Only log trade events for informational purposes; do not use for breakouts or trade history
        # logger.info(f"[Polygon] (INFO) Trade event received for {symbol}: {event}")
        # No further processing
        pass

    async def run_forever(self):
        while True:
            try:
                logger.info("[Polygon] Connecting to Polygon WebSocket...")
                async with websockets.connect(POLYGON_WS_URL) as ws:
                    self.ws = ws
                    logger.info("[Polygon] WebSocket connection established.")
                    # Authenticate
                    auth_msg = json.dumps({"action": "auth", "params": POLYGON_API_KEY})
                    logger.info(f"[Polygon] Sending auth message: {auth_msg}")
                    await ws.send(auth_msg)
                    logger.info("[Polygon] Sent auth message.")
                    self._connected = True
                    # Subscribe to any symbols already requested
                    for symbol in self._subscribed_symbols:
                        sub_msg = json.dumps({"action": "subscribe", "params": f"T.{symbol},Q.{symbol}"})
                        logger.info(f"[Polygon] Sending subscription message (reconnect): {sub_msg}")
                        await ws.send(sub_msg)
                        logger.info(f"[Polygon] Subscribed to {symbol} (trades & quotes)")
                    # Main receive loop
                    async for message in ws:
                        #logger.info(f"[Polygon] Raw message received: {message}")
                        try:
                            data = json.loads(message)
                            if not isinstance(data, list):
                                data = [data]
                            for event in data:
                                ev_type = event.get("ev")
                                symbol = event.get("sym")
                                if ev_type and symbol:
                                    if ev_type.startswith("T"):  # Trade
                                        #logger.info(f"[Polygon] Trade tick for {symbol}: {event}")
                                        await self._trade_handler(symbol, event)
                                    elif ev_type.startswith("Q"):  # Quote
                                        #logger.info(f"[Polygon] Quote tick for {symbol}: {event}")
                                        await self._quote_handler(symbol, event)
                        except Exception as e:
                            logger.error(f"[Polygon] Error parsing message: {e}\n{traceback.format_exc()}")
            except Exception as e:
                logger.error(f"[Polygon] WebSocket error: {e}. Reconnecting in 5s...")
                self._connected = False
                await asyncio.sleep(5)