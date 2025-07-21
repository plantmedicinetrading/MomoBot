# app/trading/core/candle_builder.py

import logging
from datetime import datetime
from alpaca.data.models import Quote

from ...state import ticker_states
from ..utils.time_tools import get_minute_bucket

logger = logging.getLogger(__name__)

def handle_new_quote(symbol: str, quote: Quote):
    """
    Integrates a live quote into the current 1-minute candle for a given symbol.
    If a new candle has begun, rolls over and finalizes the last one.
    """
    state = ticker_states[symbol]
    ts = quote.timestamp.replace(second=0, microsecond=0)
    price = quote.ask_price if quote.ask_price else quote.bid_price
    volume = quote.ask_size + quote.bid_size

    if 'current_candle' not in state:
        # Initialize first candle
        state['current_candle'] = {
            'timestamp': ts,
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': volume,
        }
       # logger.info(f"[{symbol}] Initial candle created at {ts}")
        return

    current = state['current_candle']

    if ts > current['timestamp']:
        # Candle closed — move to history
        if 'candles' not in state:
            state['candles'] = []
        state['candles'].append(current)
        #logger.info(f"[{symbol}] Candle closed: {current}")

        # Start a new candle
        state['current_candle'] = {
            'timestamp': ts,
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': volume,
        }
    else:
        # Update existing candle
        current['high'] = max(current['high'], price)
        current['low'] = min(current['low'], price)
        current['close'] = price
        current['volume'] += volume