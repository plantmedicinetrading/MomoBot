# app/socketio_events.py

import threading
import asyncio
from . import alpaca_stream, alpaca_loop
from .state import ticker_states
from .trading.pullbacks.tracker import PullbackTracker, Candle
from datetime import datetime
from typing import Any

pullback_trackers = {}
entry_types_map = {}

selected_ticker = None
simulate_thread = None  # no longer used, but kept for fallback if needed

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
    def handle_select_ticker(ticker):
        global selected_ticker
        selected_ticker = ticker
        print(f"📩 Ticker received and stored: {selected_ticker}")

        # Initialize ticker state if not already present
        if ticker not in ticker_states:
            ticker_states[ticker] = {
                "candles": [],
                "breakouts": [],
                "last_quote": None
            }

        socketio.emit('ticker_selected', {'ticker': selected_ticker})

        # Ensure Alpaca stream is subscribed (thread-safe via event loop)
        if alpaca_loop:
            asyncio.run_coroutine_threadsafe(
                alpaca_stream.subscribe_to_ticker(ticker),
                alpaca_loop
            )
        else:
            print("⚠️ No event loop available for Alpaca stream")

    @socketio.on('get_selected_ticker')
    def handle_get_selected_ticker():
        socketio.emit('ticker_selected', {'ticker': selected_ticker})

    @socketio.on("set_entry_type")
    def handle_set_entry_type(data):
        symbol = data.get("symbol", "").upper()
        entry_type = data.get("entry_type", "").lower()
        if symbol and entry_type in ["10s", "1m", "5m"]:
            ticker_states[symbol]["active_entry_type"] = entry_type
            print(f"[{symbol}] 🔁 Active entry type set to: {entry_type}")
            socketio.emit("entry_type_set", {"symbol": symbol, "entry_type": entry_type})
        else:
            print(f"⚠️ Invalid entry type or symbol: {entry_type}, {symbol}")

    # ✅ Allow AlpacaStream to emit updates to frontend
    alpaca_stream.set_socketio(socketio)