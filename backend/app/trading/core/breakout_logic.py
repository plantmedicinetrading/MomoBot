# app/trading/core/breakout_logic.py

import logging
from datetime import datetime, timezone

from ...state import ticker_states
from ..pullbacks.tracker import PullbackTracker, Candle
from ..core.trade_monitor import check_trade_targets  # ✅ Ensure correct import
from ..core.execution import submit_bracket_order

logger = logging.getLogger(__name__)

# Dictionary to track PullbackTracker instances
pullback_trackers = {}

def process_quote_for_breakout(symbol: str, quote):
    state = ticker_states.get(symbol)
    if not state:
        return

    candle = _get_current_candle(state)
    if not candle:
        return

    tracker = pullback_trackers.get(symbol)
    if not tracker:
        tracker = PullbackTracker(symbol)
        pullback_trackers[symbol] = tracker

    tracker.add_candle(candle)

    # ✅ Safely extract bid/ask price
    bid = getattr(quote, "bid_price", None) or getattr(quote, "bp", None)
    ask = getattr(quote, "ask_price", None) or getattr(quote, "ap", None)

    if bid is None or ask is None:
        logger.warning(f"[{symbol}] Skipping breakout check — missing bid/ask")
        return

    # ✅ Calculate midpoint and check for breakout
    midpoint = (bid + ask) / 2
    breakout_hit = tracker.check_tick_for_entry(symbol, midpoint, bid, ask)

    # ✅ If we're in a trade, check TP1/TP2/SL
    position = state.get("position")
    if position:
        try:
            check_trade_targets(symbol, position, price=midpoint)
        except Exception as e:
            logger.exception(f"[{symbol}] Failed to check trade targets", exc_info=e)

def _get_current_candle(state):
    candles = state.get("candles", [])
    if not candles:
        return None

    c = candles[-1]
    return Candle(
        timestamp=c["timestamp"],
        open=c["open"],
        high=c["high"],
        low=c["low"],
        close=c["close"],
        volume=c["volume"]
    )