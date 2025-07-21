import logging
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest, StopLimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType

from ...state import config

logger = logging.getLogger(__name__)

def submit_bracket_order(
    symbol: str,
    entry_price: float,
    size: int,
    tp1: float,
    tp2: float,
    stop: float
):
    """
    Submits a buy limit order with manual take-profit and stop-loss logic.
    This does NOT use Alpaca's native bracket order (for more control).
    """
    client = TradingClient(config["ALPACA_API_KEY"], config["ALPACA_SECRET_KEY"], paper=True)

    limit_price = round(entry_price + 0.05, 2)  # Offset entry like DAS
    order = LimitOrderRequest(
        symbol=symbol,
        qty=size,
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        time_in_force=TimeInForce.DAY,
        limit_price=limit_price
    )

    try:
        submitted = client.submit_order(order)
        logger.info(f"[{symbol}] Entry order submitted: {submitted.id}")
    except Exception as e:
        logger.exception(f"[{symbol}] Failed to submit order", exc_info=e)

def submit_order(symbol, qty, side, bid=None, ask=None):
    """
    Submits a limit order based on side and current bid/ask, with 5-cent offset.
    """
    if bid is None or ask is None:
        logger.error(f"[{symbol}] ❌ Missing bid/ask prices for limit order.")
        return None

    limit_price = round((ask + 0.05) if side == "buy" else (bid - 0.05), 2)

    order_data = LimitOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
        limit_price=limit_price,
        extended_hours=True,
    )

    try:
        client = TradingClient(config["ALPACA_API_KEY"], config["ALPACA_SECRET_KEY"], paper=True)
        order = client.submit_order(order_data)
        logger.info(f"📤 Limit order submitted for {symbol} — side: {side}, qty: {qty}, limit: {limit_price}")
        return order
    except Exception as e:
        logger.error(f"❌ Failed to submit limit order for {symbol}: {e}")
        return None

def submit_stop_limit_order(symbol, qty, stop_price, limit_price):
    """
    Submits a stop-limit order to Alpaca for use as manual SL.
    """
    order_data = StopLimitOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
        stop_price=round(stop_price, 2),
        limit_price=round(limit_price, 2),
        extended_hours=True,
    )

    try:
        client = TradingClient(config["ALPACA_API_KEY"], config["ALPACA_SECRET_KEY"], paper=True)
        order = client.submit_order(order_data)
        logger.info(f"🛑 Stop-limit submitted for {symbol} — stop: {stop_price}, limit: {limit_price}, qty: {qty}")
        return order
    except Exception as e:
        logger.error(f"❌ Failed to submit stop-limit order for {symbol}: {e}")
        return None