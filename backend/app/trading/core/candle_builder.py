# app/trading/core/candle_builder.py

import logging
from datetime import datetime
from typing import Any

from ...shared_state import ticker_states
from ..utils.time_tools import get_minute_bucket, get_10s_bucket

logger = logging.getLogger(__name__)

#ticker_states: dict[str, dict[str, Any]] = {}

def handle_new_quote(symbol: str, quote: Any):
    #logger.info(f"[{symbol}] Incoming quote: ask={quote.ask_price}, bid={quote.bid_price}, ask_size={quote.ask_size}, bid_size={quote.bid_size}, ts={quote.timestamp}")
    """
    Integrates a live quote into the current 1-minute candle for a given symbol.
    If a new candle has begun, rolls over and finalizes the last one.
    """
    if symbol not in ticker_states:
        ticker_states[symbol] = {
            "candles": [],
            "breakouts": [],
            "last_quote": None
        }
    state = ticker_states[symbol]
    # Keep timestamps in UTC for chart compatibility, but store Eastern Time for trade records
    ts = quote.timestamp.replace(second=0, microsecond=0)
    price = quote.ask_price if quote.ask_price else quote.bid_price
    volume = quote.ask_size + quote.bid_size

    if 'current_candle' not in state:
        logger.info(f"[{symbol}] Initializing first candle at {ts} with price {price}")
        # Initialize first candle
        state['current_candle'] = {
            'timestamp': ts,
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': volume,
        }
    current = state.get('current_candle')
    if current is None:
        logger.warning(f"[{symbol}] current_candle is None after initialization!")
        return
    if ts > current['timestamp']:
        logger.info(f"[{symbol}] Finalizing candle: {current}")
        if 'candles' not in state:
            state['candles'] = []
        state['candles'].append(current)
        #logger.info(f"[{symbol}] Candle closed and appended. Starting new candle at {ts} with price {price}")
        #logger.info(f"[{symbol}] Candle closed: {current}")
        logger.info(f"active_entry_type for {symbol}: {state.get('active_entry_type')}")
        # Process breakout for 1m
        from ..core.breakout_logic import process_quote_for_breakout
        process_quote_for_breakout(symbol, current)
        # --- FIX: Add finalized 1m candle to the 1m tracker ---
        from ..pullbacks.tracker import PullbackTracker, Candle
        if "pullback_tracker_1m" not in state:
            logger.info(f"[1m] Creating new PullbackTracker for {symbol}")
            state["pullback_tracker_1m"] = PullbackTracker(symbol, interval="1m")
        tracker = state["pullback_tracker_1m"]
        candle_obj = Candle(
            timestamp=current["timestamp"],
            open=current["open"],
            high=current["high"],
            low=current["low"],
            close=current["close"],
            volume=current["volume"]
        )
        tracker.add_candle(candle_obj)
        logger.info(f"[1m] Added finalized candle to tracker for {symbol} at {current['timestamp']}")
        # --- END FIX ---
        emit_candle(symbol, '1m', current)
        state['current_candle'] = {
            'timestamp': ts,
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': volume,
        }
    else:
        current['high'] = max(current['high'], price)
        current['low'] = min(current['low'], price)
        current['close'] = price
        current['volume'] += volume


def handle_new_quote_10s(symbol: str, quote: Any):
    """
    Integrates a live quote into the current 10-second candle for a given symbol.
    If a new 10s candle has begun, rolls over and finalizes the last one.
    """
    if symbol not in ticker_states:
        ticker_states[symbol] = {
            "candles_10s": [],
            "current_candle_10s": None,
            "breakouts": [],
            "last_quote": None
        }
    state = ticker_states[symbol]
    ts = quote.timestamp
    if isinstance(ts, str):
        bucket_ts = get_10s_bucket(ts)
    else:
        bucket_ts = ts.replace(second=(ts.second // 10) * 10, microsecond=0)
    price = quote.ask_price if quote.ask_price else quote.bid_price
    volume = quote.ask_size + quote.bid_size

    #logger.info(f"[10s] {symbol} quote at {ts}, bucket {bucket_ts}, price {price}")

    if state.get('current_candle_10s') is None or state['current_candle_10s']['timestamp'] != bucket_ts:
        if state.get('current_candle_10s') is not None:
            if 'candles_10s' not in state:
                state['candles_10s'] = []
            #logger.info(f"[10s] Finalized candle for {symbol}: {state['current_candle_10s']}")
            #logger.info(f"[10s] active_entry_type for {symbol}: {state.get('active_entry_type')}")
            state['candles_10s'].append(state['current_candle_10s'])
            # Process breakout for 10s
            from ..core.breakout_logic import process_quote_for_breakout_10s
            process_quote_for_breakout_10s(symbol, state['candles_10s'][-1])
            # --- FIX: Add finalized 10s candle to the 10s tracker ---
            from ..pullbacks.tracker import PullbackTracker, Candle
            if "pullback_tracker_10s" not in state:
                logger.info(f"[10s] Creating new PullbackTracker for {symbol}")
                state["pullback_tracker_10s"] = PullbackTracker(symbol, interval="10s")
            tracker = state["pullback_tracker_10s"]
            candle_obj = Candle(
                timestamp=state['current_candle_10s']["timestamp"],
                open=state['current_candle_10s']["open"],
                high=state['current_candle_10s']["high"],
                low=state['current_candle_10s']["low"],
                close=state['current_candle_10s']["close"],
                volume=state['current_candle_10s']["volume"]
            )
            tracker.add_candle(candle_obj)
            logger.info(f"[10s] Added finalized candle to tracker for {symbol} at {state['current_candle_10s']['timestamp']}")
            # --- END FIX ---
            emit_candle(symbol, '10s', state['current_candle_10s'])
        state['current_candle_10s'] = {
            'timestamp': bucket_ts,
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': volume,
        }
    else:
        c = state['current_candle_10s']
        c['high'] = max(c['high'], price)
        c['low'] = min(c['low'], price)
        c['close'] = price
        c['volume'] += volume

    # Log the current in-progress 10s candle after each quote
    #logger.info(f"[10s] Current in-progress candle for {symbol}: {state['current_candle_10s']}")


def handle_new_quote_5m(symbol: str, quote: Any):
    """
    Integrates a live quote into the current 5-minute candle for a given symbol.
    If a new 5m candle has begun, rolls over and finalizes the last one.
    """
    if symbol not in ticker_states:
        ticker_states[symbol] = {
            "candles_5m": [],
            "current_candle_5m": None,
            "breakouts": [],
            "last_quote": None
        }
    state = ticker_states[symbol]
    ts = quote.timestamp
    if isinstance(ts, str):
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    else:
        dt = ts
    bucket_minute = (dt.minute // 5) * 5
    bucket_ts = dt.replace(minute=bucket_minute, second=0, microsecond=0)
    price = quote.ask_price if quote.ask_price else quote.bid_price
    volume = quote.ask_size + quote.bid_size

    if state.get('current_candle_5m') is None or state['current_candle_5m']['timestamp'] != bucket_ts:
        # Finalize previous candle
        if state.get('current_candle_5m') is not None:
            if 'candles_5m' not in state:
                state['candles_5m'] = []
            state['candles_5m'].append(state['current_candle_5m'])
            # Process breakout for 5m
            from ..core.breakout_logic import process_quote_for_breakout_5m
            process_quote_for_breakout_5m(symbol, state['candles_5m'][-1])
            # --- FIX: Add finalized 5m candle to the 5m tracker ---
            from ..pullbacks.tracker import PullbackTracker, Candle
            if "pullback_tracker_5m" not in state:
                logger.info(f"[5m] Creating new PullbackTracker for {symbol}")
                state["pullback_tracker_5m"] = PullbackTracker(symbol, interval="5m")
            tracker = state["pullback_tracker_5m"]
            candle_obj = Candle(
                timestamp=state['current_candle_5m']["timestamp"],
                open=state['current_candle_5m']["open"],
                high=state['current_candle_5m']["high"],
                low=state['current_candle_5m']["low"],
                close=state['current_candle_5m']["close"],
                volume=state['current_candle_5m']["volume"]
            )
            tracker.add_candle(candle_obj)
            logger.info(f"[5m] Added finalized candle to tracker for {symbol} at {state['current_candle_5m']['timestamp']}")
            # --- END FIX ---
            emit_candle(symbol, '5m', state['current_candle_5m'])
        # Start new candle
        state['current_candle_5m'] = {
            'timestamp': bucket_ts,
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': volume,
        }
    else:
        # Update existing candle
        c = state['current_candle_5m']
        c['high'] = max(c['high'], price)
        c['low'] = min(c['low'], price)
        c['close'] = price
        c['volume'] += volume


def emit_candle(symbol, timeframe, candle):
    from ...socketio_events import emit_candle_update
    # Convert datetime to Unix timestamp for chart (timestamps are in UTC)
    if hasattr(candle['timestamp'], 'timestamp'):
        # If it's a datetime object, convert to Unix timestamp
        unix_time = int(candle['timestamp'].timestamp())
    else:
        # If it's already a Unix timestamp, use as is
        unix_time = int(candle['timestamp'])
    
    data = {
        'time': unix_time,
        'open': candle['open'],
        'high': candle['high'],
        'low': candle['low'],
        'close': candle['close'],
        'volume': candle.get('volume', 0)
    }
    emit_candle_update(symbol, timeframe, data)