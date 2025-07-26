# app/trading/core/breakout_logic.py

import logging
from datetime import datetime, timezone
import sys

import backend.app.shared_state as shared_state
from ..pullbacks.tracker import PullbackTracker, Candle
from ..core.trade_monitor import check_trade_targets  # ✅ Ensure correct import
from ..core.execution import submit_bracket_order
from ..core.candle_builder import handle_new_quote

logger = logging.getLogger(__name__)

def process_quote_for_breakout(symbol, quote):
    """
    Handles breakout logic for both quote objects (with .timestamp) and Polygon trade dicts.
    Only calls handle_new_quote if the input has a .timestamp attribute.
    """
    # logger.info(f"[BREAKOUT] Called for symbol={symbol}, watched_ticker={shared_state.watched_ticker}")
    if not shared_state.breakout_ready:
        logger.warning(f"[BREAKOUT] Not ready: breakout_ready is False. Skipping breakout logic.")
        return
    if shared_state.watched_ticker is None:
        logger.warning(f"[BREAKOUT] watched_ticker is None! No breakout logic will run.")
    if symbol != shared_state.watched_ticker:
        logger.info(f"[BREAKOUT] Skipping: symbol {symbol} != watched_ticker {shared_state.watched_ticker}")
        return
    state = shared_state.ticker_states.get(symbol)
    if not state:
        logger.info(f"No state for {symbol}")
        return
    bid = getattr(quote, "bid_price", None) or getattr(quote, "bp", None)
    ask = getattr(quote, "ask_price", None) or getattr(quote, "ap", None)
    # logger.info(f"[BREAKOUT] {symbol} bid={bid} ask={ask}")
    if bid is None or ask is None:
        logger.warning(f"[{symbol}] Skipping breakout check — missing bid/ask")
        return
    midpoint = (bid + ask) / 2
    entry_type = state.get("active_entry_type")
    # Always check the correct tracker for the active entry_type at tick level
    if entry_type == "10s":
        if "pullback_tracker_10s" not in state:
            state["pullback_tracker_10s"] = PullbackTracker(symbol, interval="10s")
        tracker = state["pullback_tracker_10s"]
        breakout_hit = tracker.check_tick_for_entry(symbol, midpoint, bid, ask)
        position = state.get("position")
        if position:
            try:
                check_trade_targets(symbol, midpoint, bid, ask)
            except Exception as e:
                logger.exception(f"[{symbol}] Failed to check trade targets", exc_info=e)
    elif entry_type == "1m":
        if "pullback_tracker_1m" not in state:
            state["pullback_tracker_1m"] = PullbackTracker(symbol, interval="1m")
        tracker = state["pullback_tracker_1m"]
        breakout_hit = tracker.check_tick_for_entry(symbol, midpoint, bid, ask)
        position = state.get("position")
        if position:
            try:
                check_trade_targets(symbol, midpoint, bid, ask)
            except Exception as e:
                logger.exception(f"[{symbol}] Failed to check trade targets", exc_info=e)
    elif entry_type == "5m":
        if "pullback_tracker_5m" not in state:
            state["pullback_tracker_5m"] = PullbackTracker(symbol, interval="5m")
        tracker = state["pullback_tracker_5m"]
        breakout_hit = tracker.check_tick_for_entry(symbol, midpoint, bid, ask)
        position = state.get("position")
        if position:
            try:
                check_trade_targets(symbol, midpoint, bid, ask)
            except Exception as e:
                logger.exception(f"[{symbol}] Failed to check trade targets", exc_info=e)
    else:
        # logger.info(f"[BREAKOUT] {symbol} No valid entry_type set, skipping breakout check.")
        pass

def process_quote_for_breakout_10s(symbol: str, candle_dict, tracker=None):
    logger.info(f"[BREAKOUT-10S] Called for symbol={symbol}, watched_ticker={shared_state.watched_ticker}")
    if not shared_state.breakout_ready:
        #logger.warning(f"[BREAKOUT-10S] Not ready: breakout_ready is False. Skipping breakout logic.")
        return
    if shared_state.watched_ticker is None:
        logger.warning(f"[BREAKOUT-10S] watched_ticker is None! No breakout logic will run.")
    if symbol != shared_state.watched_ticker:
        #logger.info(f"[BREAKOUT-10S] Skipping: symbol {symbol} != watched_ticker {shared_state.watched_ticker}")
        return
    from ..pullbacks.tracker import PullbackTracker, Candle
    state = shared_state.ticker_states.get(symbol)
    if not state:
        logger.info(f"No state for {symbol} (10s)")
        return
    # Convert dict to Candle object if needed
    if isinstance(candle_dict, dict):
        candle = Candle(
            timestamp=candle_dict["timestamp"],
            open=candle_dict["open"],
            high=candle_dict["high"],
            low=candle_dict["low"],
            close=candle_dict["close"],
            volume=candle_dict["volume"]
        )
    else:
        candle = candle_dict
    if "pullback_tracker_10s" not in state:
        state["pullback_tracker_10s"] = PullbackTracker(symbol, interval="10s")
    tracker = state["pullback_tracker_10s"]
    # Always add finalized candle to tracker for logging
    tracker.add_candle(candle)
    bid = state.get("last_quote").bid_price if state.get("last_quote") else None
    ask = state.get("last_quote").ask_price if state.get("last_quote") else None
    # logger.info(f"[BREAKOUT-10S] {symbol} bid={bid} ask={ask}")
    if bid is None or ask is None:
        logger.warning(f"[{symbol}] (10s) Skipping breakout check — missing bid/ask")
        return
    midpoint = (bid + ask) / 2
    entry_type = state.get("active_entry_type")
    logger.info(f"[BREAKOUT-10S] {symbol} entry_type={entry_type}")
    if entry_type is None:
        logger.warning(f"[BREAKOUT-10S] active_entry_type is None for {symbol}! No entries will be taken.")
        logger.info(f"[{symbol}] (10s) Skipping entry: active_entry_type is None")
        tracker.check_tick_for_entry(symbol, midpoint, bid, ask)
        return
    if entry_type == "10s":
        logger.info(f"[BREAKOUT-10S] {symbol} Checking for 10s breakout at price={midpoint}")
        breakout_hit = tracker.check_tick_for_entry(symbol, midpoint, bid, ask)
        # If we're in a trade, check TP1/TP2/SL (same as 1m logic)
        position = state.get("position")
        if position:
            try:
                check_trade_targets(symbol, midpoint, bid, ask)
            except Exception as e:
                logger.exception(f"[{symbol}] (10s) Failed to check trade targets", exc_info=e)
    else:
        tracker.check_tick_for_entry(symbol, midpoint, bid, ask)

def process_quote_for_breakout_5m(symbol: str, candle_dict, tracker=None):
    if symbol != shared_state.watched_ticker:
        return
    state = shared_state.ticker_states.get(symbol)
    if not state:
        logger.info(f"No state for {symbol} (5m)")
        return

    # Convert dict to Candle object if needed
    if isinstance(candle_dict, dict):
        candle = Candle(
            timestamp=candle_dict["timestamp"],
            open=candle_dict["open"],
            high=candle_dict["high"],
            low=candle_dict["low"],
            close=candle_dict["close"],
            volume=candle_dict["volume"]
        )
    else:
        candle = candle_dict

    # Use per-symbol, per-interval tracker
    if tracker is None:
        if "pullback_tracker_5m" not in state:
            state["pullback_tracker_5m"] = PullbackTracker(symbol, interval="5m")
        tracker = state["pullback_tracker_5m"]
    tracker.add_candle(candle)

    last_quote = state.get("last_quote")
    bid = getattr(last_quote, "bid_price", None) if last_quote else None
    ask = getattr(last_quote, "ask_price", None) if last_quote else None
    if bid is None or ask is None:
        logger.warning(f"[{symbol}] (5m) Skipping breakout check — missing bid/ask")
        return

    midpoint = (bid + ask) / 2
    entry_type = state.get("active_entry_type")
    if entry_type is None:
        logger.info(f"[{symbol}] (5m) Skipping entry: active_entry_type is None")
        tracker.check_tick_for_entry(symbol, midpoint, bid, ask)
        return
    if entry_type == "5m":
        breakout_hit = tracker.check_tick_for_entry(symbol, midpoint, bid, ask)
        position = state.get("position")
        if position:
            try:
                check_trade_targets(symbol, midpoint, bid, ask)
            except Exception as e:
                logger.exception(f"[{symbol}] (5m) Failed to check trade targets", exc_info=e)
    else:
        tracker.check_tick_for_entry(symbol, midpoint, bid, ask)

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