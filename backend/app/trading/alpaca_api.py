import os
import asyncio
from alpaca.data.live import StockDataStream
from dotenv import load_dotenv
from alpaca.data.enums import DataFeed
import threading

# Load API keys
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

FEED = os.getenv("ALPACA_FEED", "sip").lower()
if FEED not in ["iex", "sip"]:
    raise ValueError("ALPACA_FEED must be 'iex' or 'sip'")
feed_enum = DataFeed.IEX if FEED == "iex" else DataFeed.SIP

# Shared Alpaca stream instance
stream = StockDataStream(API_KEY, SECRET_KEY, feed=feed_enum)

# Globals to track state
socketio = None
current_symbol = None
streaming_task = None
streaming_thread = None
loop = asyncio.new_event_loop()

def run_event_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

# Start the event loop in a background thread
if streaming_thread is None:
    streaming_thread = threading.Thread(target=run_event_loop, daemon=True)
    streaming_thread.start()

async def _on_quote(data):
    print(f"📥 Quote received: {data}")
    if socketio and data.symbol == current_symbol:
        quote_data = {
            "ticker": data.symbol,
            "ask": float(data.ask_price),
            "ask_size": int(data.ask_size),
            "bid": float(data.bid_price),
            "bid_size": int(data.bid_size),
            "timestamp": str(data.timestamp)
        }
        socketio.emit("price_update", quote_data)

def start_streaming(symbol: str, sio):
    global socketio, current_symbol, streaming_task

    if symbol == current_symbol:
        return  # Already streaming this symbol

    print(f"📡 Switching stream to: {symbol}")

    # Unsubscribe from previous symbol
    if current_symbol:
        try:
            print(f"🔌 Unsubscribing from: {current_symbol}")
            coro = stream.unsubscribe_quotes(current_symbol)
            asyncio.run_coroutine_threadsafe(coro, loop)
        except Exception as e:
            print(f"⚠️ Error unsubscribing: {e}")

    socketio = sio
    current_symbol = symbol

    # Subscribe to new symbol
    try:
        print(f"📶 Subscribing to: {symbol}")
        coro = stream.subscribe_quotes(_on_quote, symbol)
        asyncio.run_coroutine_threadsafe(coro, loop)
    except Exception as e:
        print(f"⚠️ Error subscribing to new symbol: {e}")

    # Start stream only if not already running
    if not stream._running:
        try:
            print("🔄 Starting Alpaca stream")
            coro = stream._run_forever()
            asyncio.run_coroutine_threadsafe(coro, loop)
        except Exception as e:
            print(f"⚠️ Error starting stream: {e}")