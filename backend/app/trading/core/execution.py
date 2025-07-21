# app/trading/core/execution.py

import logging
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest, StopLimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType

from ...state import config, ticker_states

logger = logging.getLogger(__name__)

def submit_bracket_order(symbol, entry_price, size, tp1, tp2, stop):
    client = TradingClient(config["ALPACA_API_KEY"], config["ALPACA_SECRET_KEY"], paper=True)

    limit_price = round(entry_price + 0.05, 2)

    entry_order = LimitOrderRequest(
        symbol=symbol,
        qty=size,
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        time_in_force=TimeInForce.DAY,
        limit_price=limit_price
    )

    try:
        submitted = client.submit_order(entry_order)
        logger.info(f"[{symbol}] Entry order submitted: {submitted.id}")

        # ✅ Track the position immediately
        ticker_states[symbol]["position"] = {
            "entry_price": entry_price,
            "size": size,
            "tp1": tp1,
            "tp2": tp2,
            "stop": stop,
            "tp1_hit": False,
            "tp2_hit": False,
            "sl_hit": False,
            "status": "open"
        }

        # Submit TP1 and TP2 limit sells (half size each)
        half = size // 2
        for target_price in [tp1, tp2]:
            tp_order = LimitOrderRequest(
                symbol=symbol,
                qty=half,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
                limit_price=round(target_price, 2)
            )
            client.submit_order(tp_order)
            logger.info(f"[{symbol}] Take profit order submitted at {target_price}")

        # Submit SL stop-limit sell for full position
        sl_order = StopLimitOrderRequest(
            symbol=symbol,
            qty=size,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
            stop_price=round(stop, 2),
            limit_price=round(stop - 0.05, 2)
        )
        client.submit_order(sl_order)
        logger.info(f"[{symbol}] Stop-limit order submitted at {stop}")

    except Exception as e:
        logger.exception(f"[{symbol}] Failed to submit bracket orders", exc_info=e)