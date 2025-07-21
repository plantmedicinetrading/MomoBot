import os
import threading
import asyncio
import logging
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from .state import config
from .trading.stream.alpaca_stream import AlpacaStream

load_dotenv()

# Global shared instances
socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")
alpaca_stream = AlpacaStream()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(name)s: %(message)s'
)

alpaca_loop = None

def start_alpaca_event_loop():
    global alpaca_loop
    alpaca_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(alpaca_loop)

    async def main():
        await alpaca_stream.run_forever()

    try:
        alpaca_loop.run_until_complete(main())
    except Exception as e:
        print(f"🔥 Alpaca stream error: {e}")

def create_app():
    app = Flask(__name__)
    CORS(app)
    socketio.init_app(app)

    threading.Thread(target=start_alpaca_event_loop, daemon=True).start()

    from .routes import main_bp
    from .socketio_events import register_socket_events

    app.register_blueprint(main_bp)
    register_socket_events(socketio)

    return app