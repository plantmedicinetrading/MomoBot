# app/trading/core/execution.py

import logging
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest, StopLimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
from ...state import ticker_states
from ...config import ALPACA_API_KEY, ALPACA_SECRET_KEY

logger = logging.getLogger(__name__)
client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)


def submit_bracket_order(symbol, entry_price, qty, tp1, tp2, stop):
    try:
        order_data = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            time_in_force=TimeInForce.DAY,
            limit_price=round(entry_price, 2)
        )
        order = client.submit_order(order_data)
        logger.info(f"[{symbol}] Entry order submitted: {order.id}")

        # Track position in ticker state
        ticker_states[symbol]["position"] = {
            "entry_price": round(entry_price, 2),
            "size": qty,
            "tp1": round(tp1, 2),
            "tp2": round(tp2, 2),
            "stop": round(stop, 2),
            "tp1_hit": False,
            "tp2_hit": False,
            "sl_hit": False,
            "order_id": order.id,
        }

    except Exception as e:
        logger.exception(f"[{symbol}] ❌ Failed to submit entry order", exc_info=e)


def submit_order(symbol: str, qty: int, side: str, bid: float = None, ask: float = None):
    try:
        limit_price = ask if side == "sell" else bid
        if limit_price is None:
            logger.warning(f"[{symbol}] Cannot submit {side} order — missing bid/ask")
            return

        limit_price = round(limit_price, 2)

        order_data = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL if side == "sell" else OrderSide.BUY,
            type=OrderType.LIMIT,
            time_in_force=TimeInForce.DAY,
            limit_price=limit_price
        )
        order = client.submit_order(order_data)
        logger.info(f"[{symbol}] {side.upper()} order submitted: {order.id} at ${limit_price}")

    except Exception as e:
        logger.exception(f"[{symbol}] ❌ Failed to submit {side} order", exc_info=e)


def submit_stop_limit_order(symbol: str, qty: int, stop_price: float, limit_price: float):
    try:
        order_data = StopLimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
            stop_price=round(stop_price, 2),
            limit_price=round(limit_price, 2)
        )
        order = client.submit_order(order_data)
        logger.info(f"[{symbol}] STOP LIMIT submitted: stop={stop_price}, limit={limit_price} → {order.id}")
    except Exception as e:
        logger.exception(f"[{symbol}] ❌ Failed to submit stop-limit order", exc_info=e)