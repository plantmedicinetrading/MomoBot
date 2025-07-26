# app/trading/core/trade_update.py

from ...shared_state import ticker_states
from ..core.trade_manager import on_entry_filled
from ...db import insert_trade, insert_execution
from datetime import datetime

def handle_trade_update(data):
    """
    Handles updates from Alpaca's trade_updates stream.
    This can be extended to handle fills, cancellations, partial fills, etc.
    """
    symbol = getattr(data, 'symbol', None)
    event = getattr(data, 'event', None)
    price = getattr(data, 'price', None)
    filled_qty = getattr(data, 'filled_qty', None)  # Should be int
    side = getattr(data, 'side', None)  # 'buy' or 'sell'
    event_time = getattr(data, 'timestamp', None) or datetime.utcnow().isoformat()

    if not symbol:
        return

    print(f"[{symbol}] 🔄 Trade update event: {event}")

    # Only record executions/trades on fill events
    if event == "fill" and filled_qty and price is not None:
        # Record execution
        insert_execution({
            "symbol": symbol,
            "quantity": filled_qty,
            "price": price,
            "side": side.capitalize(),
            "datetime": str(event_time),
            "trade_id": None,
            "commission": None,
            "entry_type": None
        })
        # If this is a sell fill, try to record a trade (round trip)
        if side == "sell":
            state = ticker_states.get(symbol)
            entry_price = None
            entry_time = None
            entry_type = None
            shares = filled_qty
            # Try to find the last buy execution for this symbol
            from ...db import get_all_executions
            executions = [e for e in get_all_executions() if e["symbol"] == symbol and e["side"].lower() == "buy"]
            if executions:
                last_buy = executions[-1]
                entry_price = last_buy["price"]
                entry_time = last_buy["datetime"]
                entry_type = last_buy.get("entry_type")
            profit_loss = (price - entry_price) * shares if entry_price and price and shares else 0
            insert_trade({
                "symbol": symbol,
                "shares": shares,
                "entry_price": entry_price,
                "exit_price": price,
                "entry_type": entry_type,
                "entry_time": entry_time,
                "exit_time": str(event_time),
                "profit_loss": profit_loss
            })
        # Update state as before
        state = ticker_states.get(symbol)
        if state and state.get("position"):
            pos = state["position"]
            if side == "sell":
                pos["size"] = max(0, pos.get("size", 0) - filled_qty)
                print(f"[{symbol}] Position size after fill: {pos['size']}")
                if pos["size"] == 0:
                    print(f"[{symbol}] Position fully closed, removing from state.")
                    state["position"] = None
    elif event == "fill" and side == "buy":
        print(f"[{symbol}] ✅ Entry order filled at {price}")
        # Call on_entry_filled to submit exit orders after entry fill
        state = ticker_states.get(symbol)
        if state and state.get("position"):
            pos = state["position"]
            qty = pos.get("size", 0)
            entry_price = pos.get("entry_price", price)
            tp1 = pos.get("tp1")
            tp2 = pos.get("tp2")
            stop = pos.get("stop")
            bid = price  # Use fill price as bid/ask for now
            ask = price
            on_entry_filled(symbol, entry_price, qty, bid, ask, tp1, tp2, stop)
    elif event == "fill":
        print(f"[{symbol}] ✅ Order filled at {price}")
        # Extend with additional logic if needed


