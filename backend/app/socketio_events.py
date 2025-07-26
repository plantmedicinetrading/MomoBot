# app/socketio_events.py

import threading
import asyncio
import sys
from . import polygon_stream
from .shared_state import ticker_states
from .trading.pullbacks.tracker import PullbackTracker, Candle
from datetime import datetime
from typing import Any
import logging

logger = logging.getLogger(__name__)

pullback_trackers = {}
entry_types_map = {}

selected_ticker = None
simulate_thread = None  # no longer used, but kept for fallback if needed

def emit_price_update(symbol, ask, bid, ask_size, bid_size, timestamp):
    # Convert datetime to ISO string if needed
    if hasattr(timestamp, "isoformat"):
        timestamp = timestamp.isoformat()
    data = {
        "ticker": symbol,
        "ask": ask,
        "bid": bid,
        "ask_size": ask_size,
        
        "bid_size": bid_size,
        "timestamp": timestamp
    }
    #logger.info(f"Emitting price_update for {symbol}: {data}")
    from . import socketio
    socketio.emit('price_update', data)

def register_socket_events(socketio):
    @socketio.on('connect')
    def on_connect(auth=None):
        print("✅ Client connected")
        if selected_ticker:
            socketio.emit('ticker_selected', {'ticker': selected_ticker})

    @socketio.on('disconnect')
    def on_disconnect():
        print("❌ Client disconnected")

    @socketio.on('select_ticker')
    def handle_select_ticker(ticker, retry_count=0):
        global selected_ticker
        import backend.app.shared_state as shared_state
        selected_ticker = ticker
        shared_state.watched_ticker = ticker
        shared_state.breakout_ready = True
        print(f"[SOCKETIO] watched_ticker set to: {shared_state.watched_ticker}, breakout_ready: {shared_state.breakout_ready}")
        print(f"📩 Ticker received and stored: {selected_ticker}")

        # Initialize ticker state if not already present
        if ticker not in ticker_states:
            ticker_states[ticker] = {
                "candles": [],
                "breakouts": [],
                "last_quote": None
            }
        #print(f"ticker_states keys after select: {list(ticker_states.keys())}")
        #print(f"ticker_states id in select: {id(ticker_states)}")
        #print("state module object in select:", sys.modules.get('app.state'))
        #print("state module id in select:", id(sys.modules.get('app.state')))
        
        socketio.emit('ticker_selected', {'ticker': selected_ticker})
        
        # Ensure Alpaca stream is subscribed (thread-safe via event loop)
        from . import polygon_stream
        if polygon_stream:
            try:
                print(f"[SOCKETIO] Scheduling subscribe_to_ticker({ticker}) on event loop...")
                future = asyncio.run_coroutine_threadsafe(
                    polygon_stream.subscribe_to_ticker(ticker),
                    polygon_stream.event_loop
                )
                def log_future_result(fut):
                    try:
                        result = fut.result()
                        print(f"[SOCKETIO] subscribe_to_ticker({ticker}) completed successfully.")
                    except Exception as e:
                        print(f"[SOCKETIO] ERROR in subscribe_to_ticker({ticker}): {e}")
                future.add_done_callback(log_future_result)
            except Exception as e:
                print(f"[SOCKETIO] Exception scheduling subscribe_to_ticker({ticker}): {e}")
        else:
            if retry_count < 10:
                print(f"⚠️ No event loop available for Alpaca stream, retrying ({retry_count+1})...")
                threading.Timer(0.5, lambda: handle_select_ticker(ticker, retry_count+1)).start()
            else:
                print("❌ Failed to subscribe to ticker: Alpaca event loop not available after retries.")
                socketio.emit('error', {'message': 'Alpaca stream is still starting, please try again in a few seconds.'})

    @socketio.on('get_selected_ticker')
    def handle_get_selected_ticker():
        socketio.emit('ticker_selected', {'ticker': selected_ticker})

    @socketio.on("set_entry_type")
    def handle_set_entry_type(data):
        symbol = data.get("symbol", "").upper()
        entry_type = data.get("entry_type", "").lower()
        if symbol and entry_type in ["10s", "1m", "5m", "none"]:
            ticker_states[symbol]["active_entry_type"] = None if entry_type == "none" else entry_type
            print(f"[{symbol}] 🔁 Active entry type set to: {ticker_states[symbol]['active_entry_type']}")
            print(f"[SOCKETIO] active_entry_type for {symbol} is now: {ticker_states[symbol]['active_entry_type']}")
            socketio.emit("entry_type_set", {"symbol": symbol, "entry_type": ticker_states[symbol]["active_entry_type"] or "none"})
        else:
            print(f"⚠️ Invalid entry type or symbol: {entry_type}, {symbol}")

    # ✅ Allow AlpacaStream to emit updates to frontend
    try:
        from . import polygon_stream
        if polygon_stream is not None:
            polygon_stream.set_socketio(socketio)
        else:
            print("[Warning] polygon_stream is not initialized yet; will set socketio later.")
    except Exception as e:
        print(f"[Warning] Could not set socketio on polygon_stream: {e}")