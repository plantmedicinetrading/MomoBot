# app/trading/core/trade_monitor.py

import logging
from ...shared_state import ticker_states
from ..core.execution import submit_order, submit_stop_limit_order
from ...db import insert_trade, insert_execution
from datetime import datetime, timedelta
from ...utils.timezone_utils import get_eastern_time, to_eastern_iso
from ...utils.hotkey_utils import trigger_hotkey, trigger_hotkey_sequence
from ...utils.voice_utils import announce_trade_exit

logger = logging.getLogger(__name__)



def check_trade_targets(symbol: str, price: float, bid: float, ask: float):
    #logger.info(f"Checking trade targets for {symbol} at {price}")
    state = ticker_states.get(symbol)
    if not state or "position" not in state:
        return

    trade = state["position"]
    if trade["sl_hit"] or trade["tp2_hit"]:
        return  # Trade already closed

    # Check if 5 seconds have elapsed since trade was taken
    if "entry_timestamp" not in trade:
        # If no entry timestamp, this might be an old trade without wash trade protection
        # Skip wash trade protection for backward compatibility
        logger.info(f"[{symbol}] No entry timestamp found, skipping wash trade protection")
        return
    
    # Ensure both datetimes are timezone-aware for comparison
    current_time = get_eastern_time()
    entry_timestamp = trade["entry_timestamp"]
    
    # If entry_timestamp is naive, assume it's Eastern Time
    if entry_timestamp.tzinfo is None:
        from ...utils.timezone_utils import EASTERN_TZ
        entry_timestamp = EASTERN_TZ.localize(entry_timestamp)
    
    time_since_entry = current_time - entry_timestamp
    if time_since_entry.total_seconds() < 5:
        # Still within 5-second wash trade protection window
        remaining_time = 5 - time_since_entry.total_seconds()
        logger.info(f"[{symbol}] Wash trade protection active - {remaining_time:.1f}s remaining")
        return
    elif time_since_entry.total_seconds() < 5.1:  # Log once when protection expires
        logger.info(f"[{symbol}] Wash trade protection expired - TP/SL processing enabled")

    size = trade["size"]

    # ✅ TP1 Hit
    if not trade["tp1_hit"] and ask is not None and ask >= trade["tp1"]:
        # Send TP1 hotkey sequence FIRST: sell_ask, cancel_all, break_even - before any logging or recording
        trigger_hotkey_sequence(["sell_ask", "cancel_all", "break_even"])
        
        half = size // 2
        submit_order(symbol=symbol, qty=half, side="sell", bid=bid, ask=ask)
        trade["tp1_hit"] = True
        trade["size"] -= half  # Update remaining size
        trade["stop"] = round(trade["entry_price"], 2)  # ✅ Move stop to breakeven
        logger.info(f"✅ [{symbol}] TP1 hit at {ask}. Stop moved to breakeven.")
        
        # Announce TP1 exit with robotic voice
        announce_trade_exit(symbol, ask, "take profit one")
        # Record trade for first half
        now = to_eastern_iso()
        entry_time = trade.get("entry_time") or now
        entry_price = trade.get("entry_price")
        exit_price = ask if ask is not None else bid
        entry_type = trade.get("entry_type")
        shares = half
        profit_loss = (exit_price - entry_price) * shares if entry_price and exit_price and shares else 0
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
        # For the remaining half, update entry_time to now (for next trade record)
        trade["entry_time"] = now
        # entry_price remains the same for the second half

    # ✅ TP2 Hit
    elif trade["tp1_hit"] and not trade["tp2_hit"] and ask is not None and ask >= trade["tp2"]:
        # Send TP2 hotkey FIRST: sell_ask - before any logging or recording
        trigger_hotkey("sell_ask")
        
        remaining = trade["size"]
        if remaining > 0:
            submit_order(symbol=symbol, qty=remaining, side="sell", bid=bid, ask=ask)
        trade["tp2_hit"] = True
        logger.info(f"🏁 [{symbol}] TP2 hit at {ask}. Trade closed.")
        
        # Announce TP2 exit with robotic voice
        announce_trade_exit(symbol, ask, "take profit two")
        # Record trade in DB for remaining shares
        now = to_eastern_iso()
        entry_time = trade.get("entry_time") or now
        entry_price = trade.get("entry_price")
        exit_price = ask if ask is not None else bid
        entry_type = trade.get("entry_type")
        shares = remaining
        profit_loss = (exit_price - entry_price) * shares if entry_price and exit_price and shares else 0
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
        # Send stop loss hotkey FIRST: sell_all_bid - before any logging or recording
        trigger_hotkey("sell_all_bid")
        
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
        
        # Announce stop loss exit with robotic voice
        announce_trade_exit(symbol, price, "stop loss")
        # Record trade in DB for remaining shares
        now = to_eastern_iso()
        entry_time = trade.get("entry_time") or now
        entry_price = trade.get("entry_price")
        exit_price = ask if ask is not None else bid
        entry_type = trade.get("entry_type")
        shares = remaining
        profit_loss = (exit_price - entry_price) * shares if entry_price and exit_price and shares else 0
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