# app/trading/core/trade_monitor.py

import logging
from ...state import ticker_states
from ..core.execution import submit_order, submit_stop_limit_order

logger = logging.getLogger(__name__)

def check_trade_targets(symbol: str, price: float, bid: float, ask: float):
    state = ticker_states.get(symbol)
    if not state or "position" not in state:
        return

    trade = state["position"]
    if trade["sl_hit"] or trade["tp2_hit"]:
        return  # Trade already closed

    size = trade["size"]

    # ✅ TP1 Hit
    if not trade["tp1_hit"] and price >= trade["tp1"]:
        half = size // 2
        submit_order(symbol=symbol, qty=half, side="sell", bid=bid, ask=ask)
        trade["tp1_hit"] = True
        trade["stop"] = round(trade["entry_price"], 2)  # ✅ Move stop to breakeven
        logger.info(f"✅ [{symbol}] TP1 hit at {price}. Stop moved to breakeven.")

    # ✅ TP2 Hit
    elif trade["tp1_hit"] and not trade["tp2_hit"] and price >= trade["tp2"]:
        half = size // 2
        submit_order(symbol=symbol, qty=half, side="sell", bid=bid, ask=ask)
        trade["tp2_hit"] = True
        logger.info(f"🏁 [{symbol}] TP2 hit at {price}. Trade closed.")
        state.pop("position", None)  # ✅ Clean up

    # ✅ Stop Hit (after SL or breakeven)
    elif price <= trade["stop"]:
        submit_stop_limit_order(
            symbol=symbol,
            qty=size,
            stop_price=trade["stop"],
            limit_price=round(trade["stop"] - 0.05, 2)
        )
        trade["sl_hit"] = True
        logger.info(f"❌ [{symbol}] Stopped out at {price}. Trade closed.")
        state.pop("position", None)  # ✅ Clean up