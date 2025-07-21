# app/trading/stream/alpaca_stream.py

import asyncio
import logging

from alpaca.data.live import StockDataStream
from alpaca.data.models import Quote
from alpaca_trade_api.stream import Stream
from alpaca_trade_api.common import URL
from alpaca.data.enums import DataFeed

from ...state import config
from ..core.breakout_logic import process_quote_for_breakout
from ..core.trade_update import handle_trade_update

logger = logging.getLogger(__name__)

class AlpacaStream:
    def __init__(self):
        self.data_stream = None
        self.trade_stream = None
        self._quote_handlers = {}
        self._active_symbol = None
        self._socketio = None

    def set_socketio(self, socketio):
        self._socketio = socketio

    async def subscribe_to_ticker(self, symbol):
        await self._init_streams_if_needed()  # This must run first!

        if self._active_symbol:
            logger.info(f"[WS] Unsubscribing from {self._active_symbol}...")
            await self._unsubscribe_from_symbol(self._active_symbol)

        logger.info(f"[WS] Subscribing to {symbol} via Alpaca WebSocket...")
        self._active_symbol = symbol

        async def handler(quote):
            await self._quote_handler(quote)

        self._quote_handlers[symbol] = handler

        assert self.data_stream is not None, "data_stream not initialized"
        assert self.trade_stream is not None, "trade_stream not initialized"
        self.data_stream.subscribe_quotes(handler, symbol)
        self.trade_stream.subscribe_trade_updates(self._order_update_handler)

    async def _unsubscribe_from_symbol(self, symbol):
        assert self.data_stream is not None, "data_stream not initialized"
        if symbol in self._quote_handlers:
            self.data_stream.unsubscribe_quotes(symbol)
            del self._quote_handlers[symbol]

    async def _init_streams_if_needed(self):
        if not self.data_stream:
            logger.info("🧩 Initializing StockDataStream...")
            self.data_stream = StockDataStream(
                config["ALPACA_API_KEY"],
                config["ALPACA_SECRET_KEY"],
                feed=DataFeed(config["ALPACA_FEED"])
            )

        if not self.trade_stream:
            logger.info("🧩 Initializing Trade Stream...")
            self.trade_stream = Stream(
                key_id=config["ALPACA_API_KEY"],
                secret_key=config["ALPACA_SECRET_KEY"],
                base_url=URL(config["ALPACA_BASE_URL"]),
                data_feed=config["ALPACA_FEED"]
            )

    async def _quote_handler(self, quote: Quote):
        #logger.info(f"📥 Quote handler triggered for {quote.symbol}")
        symbol = quote.symbol
        bid = quote.bid_price
        ask = quote.ask_price
        midpoint = (bid + ask) / 2
        #logger.info(f"[RECEIVED QUOTE] {symbol} bid={bid}, ask={ask}, midpoint={midpoint}")

        try:
            process_quote_for_breakout(symbol, quote)
        except Exception as e:
            logger.exception(f"❌ Error handling quote for {symbol}", exc_info=e)

    async def _order_update_handler(self, update):
        try:
            handle_trade_update(update)
        except Exception as e:
            logger.exception("❌ Error handling trade update", exc_info=e)

    async def run_forever(self):
        logger.info("✅ WebSocket run_forever coroutine started")
        await self._init_streams_if_needed()
        assert self.data_stream is not None, "data_stream not initialized"
        assert self.trade_stream is not None, "trade_stream not initialized"
        logger.info("🚀 Starting Alpaca WebSocket streams...")
        await asyncio.gather(
            self.data_stream._run_forever(),
            self.trade_stream._run_forever()
        )
        logger.info("❌ WebSocket streams exited unexpectedly.")