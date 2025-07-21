import os
import asyncio
import threading
from dotenv import load_dotenv
from alpaca.data.live import StockDataStream
from alpaca.data.enums import DataFeed
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest, StopLimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from .pullbacks.tracker import PullbackTracker, Candle
from datetime import datetime
from collections import defaultdict
import pytz

# === Load API keys ===
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# === Determine feed type ===
FEED = os.getenv("ALPACA_FEED", "sip").lower()
if FEED not in ["iex", "sip"]:
    raise ValueError("ALPACA_FEED must be 'iex' or 'sip'")
feed_enum = DataFeed.IEX if FEED == "iex" else DataFeed.SIP

# === Alpaca stream and trading client setup ===
stream = StockDataStream(API_KEY, SECRET_KEY, feed=feed_enum)
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)

# === Globals to manage state ===
socketio = None
current_symbol = None
streaming_thread = None
loop = asyncio.new_event_loop()
pullback_trackers = {}
active_trades = {}

# Track current 1-minute candle data per symbol
current_candles = {}
current_candle_minute = {}

# === Ensure background event loop is running ===
def run_event_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

if streaming_thread is None:
    streaming_thread = threading.Thread(target=run_event_loop, daemon=True)
    streaming_thread.start()

# === Submit Alpaca Limit Order (replicates DAS logic) ===
def submit_order(symbol, qty, side, bid=None, ask=None):
    if bid is None or ask is None:
        print("❌ Missing bid/ask prices for limit order.")
        return None

    limit_price = round((ask + 0.05) if side == "buy" else (bid - 0.05), 2)

    order_data = LimitOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
        limit_price=limit_price,
        extended_hours=True
    )

    try:
        order = trading_client.submit_order(order_data)
        print(f"📤 Limit order submitted for {symbol} — side: {side}, qty: {qty}, limit_price: {limit_price}")
        return order
    except Exception as e:
        print(f"❌ Failed to place limit order for {symbol}: {e}")
        return None

# === Submit Stop-Limit Order for Stop Loss ===
def submit_stop_limit_order(symbol, qty, stop_price, limit_price):
    order_data = StopLimitOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
        stop_price=round(stop_price, 2),
        limit_price=round(limit_price, 2),
        extended_hours=True
    )
    try:
        order = trading_client.submit_order(order_data)
        print(f"🛑 Stop-limit submitted for {symbol} — stop: {stop_price}, limit: {limit_price}, qty: {qty}")
        return order
    except Exception as e:
        print(f"❌ Failed to place stop-limit for {symbol}: {e}")
        return None

# === Handle incoming quote updates ===
async def _on_quote(data):
    if socketio and data.symbol == current_symbol:
        symbol = data.symbol
        timestamp = data.timestamp
        bid = float(data.bid_price)
        ask = float(data.ask_price)

        # Emit live quote
        quote_data = {
            "ticker": symbol,
            "ask": ask,
            "ask_size": int(data.ask_size),
            "bid": bid,
            "bid_size": int(data.bid_size),
            "timestamp": str(timestamp)
        }
        socketio.emit("price_update", quote_data)

        # Minute bucket (e.g., 11:42:00)
        minute_bucket = timestamp.replace(second=0, microsecond=0)

        # Start new candle or continue updating
        if symbol not in current_candles or current_candle_minute[symbol] != minute_bucket:
            if symbol in current_candles:
                candle_data = current_candles[symbol]
                candle = Candle(
                    timestamp=current_candle_minute[symbol],
                    open=candle_data["open"],
                    high=candle_data["high"],
                    low=candle_data["low"],
                    close=candle_data["close"],
                    volume=0
                )
                if symbol not in pullback_trackers:
                    pullback_trackers[symbol] = PullbackTracker(symbol)
                pullback_trackers[symbol].add_candle(candle)

            current_candles[symbol] = {
                "open": bid,
                "high": max(bid, ask),
                "low": min(bid, ask),
                "close": ask
            }
            current_candle_minute[symbol] = minute_bucket
        else:
            candle_data = current_candles[symbol]
            candle_data["high"] = max(candle_data["high"], bid, ask)
            candle_data["low"] = min(candle_data["low"], bid, ask)
            candle_data["close"] = ask

        # === Tick-based entry detection ===
        price = ask
        tracker = pullback_trackers.get(symbol)

        if tracker:
            breakout_triggered = tracker.check_tick_for_entry(price)

            if breakout_triggered:
                if symbol in active_trades:
                    print(f"⚠️ Breakout detected for {symbol}, but position already open — ignoring new entry.")
                else:
                    entry_price = price
                    stop_loss = round(entry_price - 0.10, 2)
                    target_1 = round(entry_price + 0.10, 2)
                    target_2 = round(entry_price + 0.30, 2)

                    print(f"🚀 Entry signal for {symbol} at ${entry_price}!")
                    submit_order(symbol=symbol, qty=1000, side="buy", bid=bid, ask=ask)

                    active_trades[symbol] = {
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'target_1': target_1,
                        'target_2': target_2,
                        'total_position': 1000,
                        'half_closed': False
                    }

                    socketio.emit('entry_signal', {
                        'ticker': symbol,
                        'entry_type': '1-min pullback',
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'target_1': target_1,
                        'target_2': target_2,
                        'time': timestamp.astimezone(pytz.timezone("America/New_York")).strftime("%Y-%m-%d %H:%M:%S")
                    })

        # === Live trade management ===
        if symbol in active_trades:
            trade = active_trades[symbol]
            total_position = trade['total_position']

            if price <= trade['stop_loss']:
                stop_price = trade['stop_loss']
                limit_price = round(stop_price - 0.05, 2)
                submit_stop_limit_order(symbol, qty=total_position, stop_price=stop_price, limit_price=limit_price)
                socketio.emit('trade_exit', {
                    'ticker': symbol,
                    'exit_reason': 'stop_loss',
                    'price': price
                })
                print(f"❌ {symbol} stopped out at {price}")
                del active_trades[symbol]

            elif price >= trade['target_1'] and not trade['half_closed']:
                tp1_qty = total_position // 2
                submit_order(symbol, qty=tp1_qty, side="sell", bid=bid, ask=ask)
                socketio.emit('partial_exit', {
                    'ticker': symbol,
                    'exit_reason': 'target_1',
                    'price': price
                })
                print(f"✅ {symbol} hit TP1 at {price} — stop moved to breakeven")
                trade['half_closed'] = True
                trade['stop_loss'] = round(trade['entry_price'], 2)

            elif price >= trade['target_2'] and trade['half_closed']:
                tp2_qty = total_position // 2
                submit_order(symbol, qty=tp2_qty, side="sell", bid=bid, ask=ask)
                socketio.emit('trade_exit', {
                    'ticker': symbol,
                    'exit_reason': 'target_2',
                    'price': price
                })
                print(f"🏊 {symbol} hit TP2 at {price} — full exit")
                del active_trades[symbol]

# === Start streaming quotes ===
def start_streaming(symbol: str, sio):
    global socketio, current_symbol

    if symbol == current_symbol:
        return

    print(f"📱 Switching stream to: {symbol}")

    if current_symbol:
        try:
            print(f"🔌 Unsubscribing from: {current_symbol}")
            coro = stream.unsubscribe_quotes(current_symbol)
            asyncio.run_coroutine_threadsafe(coro, loop)
        except Exception as e:
            print(f"⚠️ Error unsubscribing: {e}")

    socketio = sio
    current_symbol = symbol

    try:
        print(f"🛌 Subscribing to: {symbol}")
        coro = stream.subscribe_quotes(_on_quote, symbol)
        asyncio.run_coroutine_threadsafe(coro, loop)
    except Exception as e:
        print(f"⚠️ Error subscribing: {e}")

    if not stream._running:
        try:
            print("🔄 Starting Alpaca stream")
            coro = stream._run_forever()
            asyncio.run_coroutine_threadsafe(coro, loop)
        except Exception as e:
            print(f"⚠️ Error starting stream: {e}")