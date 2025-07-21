# app/trading/core/trade_update.py

from app.state import ticker_states

def handle_trade_update(data):
    """
    Handles updates from Alpaca's trade_updates stream.
    This can be extended to handle fills, cancellations, partial fills, etc.
    """
    event = data.get("event")
    symbol = data.get("order", {}).get("symbol")

    if not symbol:
        return

    print(f"[{symbol}] 🔄 Trade update event: {event}")

    # Optionally track fill status or update trade state here
    if event == "fill":
        print(f"[{symbol}] ✅ Order filled at {data['price']}")
        # Extend with additional logic if needed