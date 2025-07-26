from collections import defaultdict

from typing import Any

watched_ticker = None
breakout_ready = False

def default_symbol_state():
    return {
        "active_entry_type": None,  # "10s", "1m", or "5m"
        "position": None,           # Active position info
        "candles_10s": [],
        "current_candle_10s": None,
        "candles_1m": [],
        "current_candle_1m": None,
        "candles_5m": [],
        "current_candle_5m": None,
        "breakouts": [],
        "last_quote": None,
        # ... any other per-symbol state ...
    }

ticker_states = defaultdict(default_symbol_state)