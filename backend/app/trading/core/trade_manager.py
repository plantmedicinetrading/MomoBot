# app/trading/core/trade_manager.py

import logging

from ...state import active_trades
from ...shared_state import ticker_states
from ..core.execution import submit_bracket_order, submit_order, submit_stop_limit_order

logger = logging.getLogger(__name__)

def handle_breakout_trigger(symbol: str, entry_price: float, entry_type: str, bid: float, ask: float):
    # Prevent multiple open positions
    for sym, state in ticker_states.items():
        if state.get("position") is not None and sym != symbol:
            logger.warning(f"Cannot open new position for {symbol} while {sym} is still open.")
            return  # Block new entry
    logger.info(f"[{symbol}] Handling breakout trigger for {entry_type} at {entry_price}")
    """
    Called when a breakout is detected. Submits entry order and updates state.
    """
    state = ticker_states[symbol]

    # Example size — this should be configurable per symbol
    position_size = state.get("position_size", 1000)

    # Prevent duplicate trades for the same ticker
    if "position" in state and state["position"] is not None:
        logger.warning(f"[{symbol}] Trade already open. Ignoring new breakout trigger.")
        return

    # TP/SL rules
    tp1 = round(entry_price + 0.15, 2)
    tp2 = round(entry_price + 0.30, 2)
    stop = round(entry_price - 0.10, 2)

    logger.info(
        f"[{symbol}] Submitting breakout order — Size: {position_size}, "
        f"Entry: {entry_price}, TP1: {tp1}, TP2: {tp2}, SL: {stop}"
    )

    # Submit entry order (limit buy)
    entry_order = submit_order(symbol, position_size, "buy", bid, ask)
    # Store entry order ID for tracking
    state["entry_order_id"] = getattr(entry_order, "id", None)

    # Update state for tracking
    state["position"] = {
        "entry_type": entry_type,
        "entry_price": entry_price,
        "size": position_size,
        "tp1": tp1,
        "tp2": tp2,
        "stop": stop,
        "tp1_hit": False,
        "tp2_hit": False,
        "sl_hit": False,
        "tp1_order_id": None,
        "tp2_order_id": None,
        "sl_order_id": None,
        "half_closed": False
    }

    # Optionally disable further breakout triggers for this entry type
    if entry_type in state:
        state[entry_type]["triggered"] = True

    active_trades[symbol] = {
        "entry_type": entry_type,
        "entry_price": entry_price,
        "stop_loss": stop,
        "target_1": tp1,
        "target_2": tp2,
        "total_position": position_size,
        "half_closed": False
    }

def on_entry_filled(symbol, entry_price, qty, bid, ask, tp1, tp2, stop):
    logger.info(f"[{symbol}] Entry filled at {entry_price} with qty {qty}")
    """
    Called when the entry order is filled. Submits TP1, TP2, and SL orders and stores their IDs in state.
    """
    state = ticker_states[symbol]
    if qty <= 0:
        logger.warning(f"[{symbol}] No shares filled, skipping exit order submission.")
        return
    # Submit TP1 for half the filled qty
    tp1_qty = qty // 2
    tp2_qty = qty - tp1_qty  # Remaining shares for TP2
    tp1_order = submit_order(symbol, tp1_qty, "sell", bid, tp1) if tp1_qty > 0 else None
    state["position"]["tp1_order_id"] = getattr(tp1_order, "id", None) if tp1_order else None
    # Submit TP2 for the other half
    tp2_order = submit_order(symbol, tp2_qty, "sell", bid, tp2) if tp2_qty > 0 else None
    state["position"]["tp2_order_id"] = getattr(tp2_order, "id", None) if tp2_order else None
    # Submit SL for the total filled qty
    sl_order = submit_stop_limit_order(symbol, qty, stop_price=stop, limit_price=stop - 0.05)
    state["position"]["sl_order_id"] = getattr(sl_order, "id", None) if sl_order else None

def on_tp1_filled(symbol, sl_order_id, qty, entry_price):
    logger.info(f"[{symbol}] TP1 filled at {entry_price} with qty {qty}")
    """
    Called when TP1 is filled. Cancels old SL and submits new SL at breakeven for remaining qty.
    """
    state = ticker_states[symbol]
    # # Cancel old SL order
    # cancel_order(sl_order_id)
    # # Submit new SL at breakeven for remaining qty
    # new_sl_order = submit_stop_limit_order(symbol, qty // 2, stop_price=entry_price, limit_price=entry_price - 0.05)
    # state["position"]["sl_order_id"] = getattr(new_sl_order, "id", None)