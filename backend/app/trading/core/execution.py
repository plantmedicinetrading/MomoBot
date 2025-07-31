# app/trading/core/execution.py

import logging
from datetime import datetime
from ...shared_state import ticker_states
from ...db import insert_trade, insert_execution
from ...utils.hotkey_utils import trigger_hotkey

logger = logging.getLogger(__name__)

def submit_bracket_order(symbol: str, entry: float, qty: int, tp1: float, tp2: float, stop: float):
    logger.info(f"[{symbol}] (SIM) Bracket order: entry={entry}, qty={qty}, tp1={tp1}, tp2={tp2}, stop={stop}")
    ticker_states[symbol]["position"] = {
        "entry_price": entry,
        "size": qty,
        "tp1": tp1,
        "tp2": tp2,
        "stop": stop,
        "tp1_hit": False,
        "tp2_hit": False,
        "sl_hit": False,
        "order_id": None,
        "entry_timestamp": datetime.utcnow()  # Track when trade was taken for wash trade protection
    }
    # Optionally record to DB
    insert_execution({
        "symbol": symbol,
        "quantity": qty,
        "price": entry,
        "side": "buy",
        "datetime": "simulated",
        "trade_id": None,
        "commission": None,
        "entry_type": None
    })

def submit_order(symbol: str, qty: int, side: str, bid: float, ask: float):
    # Send hotkey FIRST for buy orders (entry) - before any logging or recording
    if side.lower() == "buy":
        trigger_hotkey("buy_ask")
    
    price = round(bid if side == "sell" else ask, 2)
    logger.info(f"[{symbol}] (SIM) {side.upper()} order: qty={qty} @ ${price}")
    
    insert_execution({
        "symbol": symbol,
        "quantity": qty,
        "price": price,
        "side": side.lower(),
        "datetime": "simulated",
        "trade_id": None,
        "commission": None,
        "entry_type": None
    })
    return {"symbol": symbol, "qty": qty, "side": side, "price": price, "simulated": True}

def submit_stop_limit_order(symbol: str, qty: int, stop_price: float, limit_price: float):
    # Send hotkey FIRST for stop limit orders (stop loss) - before any logging or recording
    trigger_hotkey("sell_all_bid")
    
    logger.info(f"[{symbol}] (SIM) Stop-limit order: qty={qty}, stop={stop_price}, limit={limit_price}")
    
    insert_execution({
        "symbol": symbol,
        "quantity": qty,
        "price": stop_price,
        "side": "sell",
        "datetime": "simulated",
        "trade_id": None,
        "commission": None,
        "entry_type": None
    })
    return {"symbol": symbol, "qty": qty, "side": "sell", "price": stop_price, "simulated": True}