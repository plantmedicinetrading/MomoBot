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
        self.quote_stream = None
        self.trade_stream = None
        self._quote_handlers = {}
        self._active_symbol = None
        self._socketio = None  # Optional: for frontend updates

    def set_socketio(self, socketio):
        self._socketio = socketio

    async def subscribe_to_ticker(self, symbol):
        if self._active_symbol:
            logger.info(f"[WS] Unsubscribing from {self._active_symbol}...")
            await self._unsubscribe_from_symbol(self._active_symbol)

            logger.info(f"[WS] Subscribing to {symbol} via Alpaca WebSocket...")
            await self._init_streams_if_needed()

            self._active_symbol = symbol

            # Define sync wrapper early and register it before subscribing
            def sync_wrapper(quote):
                asyncio.get_event_loop().create_task(self._quote_handler(quote))

            self._quote_handlers[symbol] = sync_wrapper

            # ✅ Use `subscribe_quotes` AFTER storing the handler
            await self.quote_stream.subscribe_quotes(sync_wrapper, symbol)
            await self.trade_stream.subscribe_trade_updates(self._order_update_handler)

    async def _unsubscribe_from_symbol(self, symbol):
        if symbol in self._quote_handlers:
            await self.quote_stream.unsubscribe_quotes(symbol)
            del self._quote_handlers[symbol]

    async def _init_streams_if_needed(self):
        if not self.quote_stream:
            self.quote_stream = StockDataStream(
                config["ALPACA_API_KEY"],
                config["ALPACA_SECRET_KEY"],
                feed=DataFeed(config["ALPACA_FEED"])
            )

        if not self.trade_stream:
            self.trade_stream = Stream(
                key_id=config["ALPACA_API_KEY"],
                secret_key=config["ALPACA_SECRET_KEY"],
                base_url=URL(config["ALPACA_BASE_URL"]),
                data_feed=config["ALPACA_FEED"]
            )

    async def _quote_handler(self, quote: Quote):
        symbol = quote.symbol
        bid = quote.bid_price
        ask = quote.ask_price
        midpoint = (bid + ask) / 2
        logger.info(f"[RECEIVED QUOTE] {symbol} bid={bid}, ask={ask}, midpoint={midpoint}")  # CHANGED: info log

        try:
            process_quote_for_breakout(symbol, quote)
        except Exception as e:
            logger.exception(f"❌ Error handling quote for {symbol}", exc_info=e)

    async def _order_update_handler(self, update):
        try:
            await handle_trade_update(update)
        except Exception as e:
            logger.exception("❌ Error handling trade update", exc_info=e)

    async def run_forever(self):
        await self._init_streams_if_needed()
        logger.info("🚀 Starting Alpaca WebSocket streams...")
        await asyncio.gather(
            self.quote_stream._run_forever(),
            self.trade_stream._run_forever()
        )