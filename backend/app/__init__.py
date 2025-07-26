import os
import threading
import asyncio
import logging
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from .state import config
from .trading.stream.polygon_stream import PolygonStream

load_dotenv()

# Global shared instances
socketio = SocketIO(cors_allowed_origins="*")
polygon_stream = PolygonStream()
# Do not set socketio or subscribe to any ticker until select_ticker is received

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(name)s: %(message)s'
)
# Explicitly set tracker logger to INFO
logging.getLogger('backend.app.trading.pullbacks.tracker').setLevel(logging.INFO)

def sync_state_with_broker():
    """Fetch all open positions from Alpaca and populate ticker_states."""
    try:
        from .brokers.alpaca_broker import AlpacaBroker
        from .shared_state import ticker_states
        from .state import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL
        broker = AlpacaBroker(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
        positions = broker.get_positions()
        for pos in positions:
            symbol = pos.symbol.upper()
            ticker_states[symbol]["position"] = {
                "entry_price": float(getattr(pos, "avg_entry_price", 0)),
                "size": int(getattr(pos, "qty", 0)),
                "entry_type": "unknown",  # Can't infer from broker
                "tp1": None, "tp2": None, "stop": None,
                "tp1_hit": False, "tp2_hit": False, "sl_hit": False,
                "alpaca_order_id": getattr(pos, 'id', None)
            }
        print(f"[State Sync] Synced {len(positions)} open positions from broker.")
    except Exception as e:
        print(f"[State Sync] Failed to sync positions from broker: {e}")

def start_polygon_event_loop():
    loop = asyncio.new_event_loop()
    polygon_stream.event_loop = loop  # Store the event loop for cross-thread scheduling
    asyncio.set_event_loop(loop)
    loop.run_until_complete(polygon_stream.run_forever())

polygon_thread = threading.Thread(target=start_polygon_event_loop, daemon=True)
polygon_thread.start()

def create_app():
    app = Flask(__name__)
    CORS(app)
    socketio.init_app(app)

    sync_state_with_broker()  # <-- Sync state before starting event loop

    from .routes import main_bp
    from .socketio_events import register_socket_events

    app.register_blueprint(main_bp)
    register_socket_events(socketio)

    return app