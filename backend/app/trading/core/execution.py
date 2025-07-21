# app/trading/core/execution.py

import logging
from alpaca_trade_api.rest import REST

from ...state import ticker_states, ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL

logger = logging.getLogger(__name__)

# ✅ Initialize Alpaca REST client (paper trading assumed)
alpaca = REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)

def submit_bracket_order(symbol: str, entry: float, qty: int, tp1: float, tp2: float, stop: float):
    try:
        limit_price = round(entry + 0.05, 2)

        order = alpaca.submit_order(
            symbol=symbol,
            qty=qty,
            side="buy",
            type="limit",
            time_in_force="day",
            limit_price=limit_price
        )

        ticker_states[symbol]["position"] = {
            "entry_price": entry,
            "size": qty,
            "tp1": tp1,
            "tp2": tp2,
            "stop": stop,
            "tp1_hit": False,
            "tp2_hit": False,
            "sl_hit": False,
            "alpaca_order_id": order.id
        }

        logger.info(f"[{symbol}] ✅ Bracket order submitted — ID: {order.id}")

    except Exception as e:
        logger.exception(f"❌ Failed to submit bracket order for {symbol}", exc_info=e)

def submit_order(symbol: str, qty: int, side: str, bid: float, ask: float):
    try:
        price = round(bid if side == "sell" else ask, 2)

        order = alpaca.submit_order(
            symbol=symbol,
            qty=qty,
            side=side.lower(),
            type="limit",
            time_in_force="day",
            limit_price=price
        )

        logger.info(f"[{symbol}] {side.upper()} order submitted — ID: {order.id} @ ${price}")

    except Exception as e:
        logger.exception(f"❌ Failed to submit {side} order for {symbol}", exc_info=e)

def submit_stop_limit_order(symbol: str, qty: int, stop_price: float, limit_price: float):
    try:
        order = alpaca.submit_order(
            symbol=symbol,
            qty=qty,
            side="sell",
            type="stop_limit",
            time_in_force="day",
            stop_price=round(stop_price, 2),
            limit_price=round(limit_price, 2)
        )

        logger.info(f"[{symbol}] 🛑 Stop-limit order submitted — ID: {order.id}")

    except Exception as e:
        logger.exception(f"❌ Failed to submit stop-limit order for {symbol}", exc_info=e)