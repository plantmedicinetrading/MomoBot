# app/trading/stream/alpaca_stream.py

import asyncio
import logging
from datetime import datetime
from alpaca.data.live import StockDataStream
from alpaca.data.enums import DataFeed
from alpaca.data.models import Quote

from ...state import config, ticker_states
from ..core.candle_builder import handle_new_quote
from ..core.breakout_logic import process_quote_for_breakout

logger = logging.getLogger(__name__)

class AlpacaStream:
    """Handles real-time Alpaca WebSocket quote streaming."""

    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.socketio = None  # 👈 Will be injected later

        # Determine feed type (sip or iex)
        feed_str = config.get("ALPACA_FEED", "sip").lower()
        if feed_str not in ["iex", "sip"]:
            raise ValueError("ALPACA_FEED must be either 'iex' or 'sip'")

        feed = DataFeed.IEX if feed_str == "iex" else DataFeed.SIP
        self.stream = StockDataStream(api_key, secret_key, feed=feed, raw_data=False)
        self.subscribed = set()

    def set_socketio(self, socketio_instance):
        """Inject socketio instance for emitting."""
        self.socketio = socketio_instance

    async def subscribe_to_ticker(self, symbol: str):
        """Subscribes to quote updates for a specific ticker."""
        if symbol in self.subscribed:
            logger.info(f"[WS] Already subscribed to {symbol}")
            return

        logger.info(f"[WS] Subscribing to {symbol} via Alpaca WebSocket...")
        self.stream.subscribe_quotes(self._quote_handler, symbol)
        self.subscribed.add(symbol)

    async def run_forever(self):
        """Starts the Alpaca WebSocket stream."""
        try:
            logger.info("🔄 Starting Alpaca WebSocket stream...")
            await self.stream._run_forever()
        except Exception as e:
            logger.exception("💥 Alpaca stream crashed", exc_info=e)

    async def _quote_handler(self, quote: Quote):
        """Processes incoming quote data for a ticker."""
        symbol = quote.symbol

        bid = getattr(quote, "bid_price", None)
        ask = getattr(quote, "ask_price", None)

        if bid is None or ask is None:
            logger.warning(f"[{symbol}] Ignoring quote with missing bid/ask → bid: {bid}, ask: {ask}")
            return

        logger.debug(f"[WS] Quote received for {symbol} → Bid: {bid}, Ask: {ask}")

        if symbol not in ticker_states:
            logger.debug(f"⚠️ Received quote for unsubscribed ticker: {symbol}")
            return

        try:
            handle_new_quote(symbol, quote)
            process_quote_for_breakout(symbol, quote)

            # Emit quote data to frontend
            if self.socketio:
                self.socketio.emit('price_update', {
                    "ticker": symbol,
                    "ask": ask,
                    "ask_size": quote.ask_size,
                    "bid": bid,
                    "bid_size": quote.bid_size,
                    "timestamp": datetime.utcnow().isoformat()
                })
        except Exception as e:
            logger.exception(f"❌ Error handling quote for {symbol}", exc_info=e)