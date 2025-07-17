import threading
from .trading import alpaca_api

selected_ticker = None
simulate_thread = None  # no longer used, but kept for fallback if needed

def register_socket_events(socketio):
    @socketio.on('connect')
    def on_connect(auth=None):
        print("✅ Client connected")

        if selected_ticker:
            # On reconnect, tell frontend what the current ticker is
            socketio.emit('ticker_selected', {'ticker': selected_ticker})

    @socketio.on('disconnect')
    def on_disconnect():
        print("❌ Client disconnected")

    @socketio.on('select_ticker')
    def handle_select_ticker(ticker):
        global selected_ticker
        selected_ticker = ticker
        print(f"📩 Ticker received and stored: {selected_ticker}")

        socketio.emit('ticker_selected', {'ticker': selected_ticker})

        # Start streaming live quotes for this ticker
        alpaca_api.start_streaming(ticker, socketio)

    @socketio.on('get_selected_ticker')
    def handle_get_selected_ticker():
        socketio.emit('ticker_selected', {'ticker': selected_ticker})