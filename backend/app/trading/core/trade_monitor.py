# app/trading/core/trade_monitor.py

import logging
from ...shared_state import ticker_states
from ..core.execution import submit_order, submit_stop_limit_order
from ...db import insert_trade, insert_execution
from datetime import datetime

logger = logging.getLogger(__name__)

def check_trade_targets(symbol: str, price: float, bid: float, ask: float):
    #logger.info(f"Checking trade targets for {symbol} at {price}")
    state = ticker_states.get(symbol)
    if not state or "position" not in state:
        return

    trade = state["position"]
    if trade["sl_hit"] or trade["tp2_hit"]:
        return  # Trade already closed

    size = trade["size"]

    # ✅ TP1 Hit
    if not trade["tp1_hit"] and ask is not None and ask >= trade["tp1"]:
        half = size // 2
        submit_order(symbol=symbol, qty=half, side="sell", bid=bid, ask=ask)
        trade["tp1_hit"] = True
        trade["size"] -= half  # Update remaining size
        trade["stop"] = round(trade["entry_price"], 2)  # ✅ Move stop to breakeven
        logger.info(f"✅ [{symbol}] TP1 hit at {ask}. Stop moved to breakeven.")

    # ✅ TP2 Hit
    elif trade["tp1_hit"] and not trade["tp2_hit"] and ask is not None and ask >= trade["tp2"]:
        remaining = trade["size"]
        if remaining > 0:
            submit_order(symbol=symbol, qty=remaining, side="sell", bid=bid, ask=ask)
        trade["tp2_hit"] = True
        logger.info(f"🏁 [{symbol}] TP2 hit at {ask}. Trade closed.")
        # Record trade in DB
        now = datetime.utcnow().isoformat()
        entry_time = trade.get("entry_time") or now
        entry_price = trade.get("entry_price")
        exit_price = bid if bid is not None else ask
        entry_type = trade.get("entry_type")
        shares = trade.get("size", 0)
        profit_loss = (exit_price - entry_price) * shares if entry_price and exit_price and shares else 0
        # Insert executions
        insert_execution({
            "symbol": symbol,
            "quantity": shares,
            "price": entry_price,
            "side": "Buy",
            "datetime": entry_time,
            "trade_id": None,
            "commission": None,
            "entry_type": entry_type
        })
        insert_execution({
            "symbol": symbol,
            "quantity": shares,
            "price": exit_price,
            "side": "Sell",
            "datetime": now,
            "trade_id": None,
            "commission": None,
            "entry_type": entry_type
        })
        insert_trade({
            "symbol": symbol,
            "shares": shares,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "entry_type": entry_type,
            "entry_time": entry_time,
            "exit_time": now,
            "profit_loss": profit_loss
        })
        state.pop("position", None)  # ✅ Clean up

    # ✅ Stop Hit (after SL or breakeven)
    elif price <= trade["stop"]:
        remaining = trade["size"]
        if remaining > 0:
            submit_order(
                symbol=symbol,
                qty=remaining,
                side="sell",
                bid=bid,
                ask=ask
            )
        trade["sl_hit"] = True
        logger.info(f"❌ [{symbol}] Stopped out at {price}. Trade closed.")
        # Record trade in DB
        now = datetime.utcnow().isoformat()
        entry_time = trade.get("entry_time") or now
        entry_price = trade.get("entry_price")
        exit_price = bid if bid is not None else ask
        entry_type = trade.get("entry_type")
        shares = trade.get("size", 0)
        profit_loss = (exit_price - entry_price) * shares if entry_price and exit_price and shares else 0
        # Insert executions
        insert_execution({
            "symbol": symbol,
            "quantity": shares,
            "price": entry_price,
            "side": "Buy",
            "datetime": entry_time,
            "trade_id": None,
            "commission": None,
            "entry_type": entry_type
        })
        insert_execution({
            "symbol": symbol,
            "quantity": shares,
            "price": exit_price,
            "side": "Sell",
            "datetime": now,
            "trade_id": None,
            "commission": None,
            "entry_type": entry_type
        })
        insert_trade({
            "symbol": symbol,
            "shares": shares,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "entry_type": entry_type,
            "entry_time": entry_time,
            "exit_time": now,
            "profit_loss": profit_loss
        })
        state.pop("position", None)  # ✅ Clean up