# app/trading/core/trade_manager.py

import logging

from ...state import ticker_states, active_trades
from ..core.execution import submit_bracket_order, submit_order, submit_stop_limit_order

logger = logging.getLogger(__name__)

def handle_breakout_trigger(symbol: str, entry_price: float, entry_type: str):
    """
    Called when a breakout is detected. Submits bracket order and updates state.
    """
    state = ticker_states[symbol]

    # Example size — this should be configurable per symbol
    position_size = state.get("position_size", 1000)

    # TP/SL rules
    tp1 = round(entry_price + 0.10, 2)
    tp2 = round(entry_price + 0.30, 2)
    stop = round(entry_price - 0.10, 2)

    logger.info(
        f"[{symbol}] Submitting breakout order — Size: {position_size}, "
        f"Entry: {entry_price}, TP1: {tp1}, TP2: {tp2}, SL: {stop}"
    )

    # Call execution layer to submit bracket order
    submit_bracket_order(symbol, entry_price, position_size, tp1, tp2, stop)

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