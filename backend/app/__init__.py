# app/__init__.py

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

# ✅ Load .env file early in the app lifecycle
load_dotenv()


# Global shared instances
socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")  # Explicitly use threading mode
alpaca_stream = AlpacaStream(
    api_key=config["ALPACA_API_KEY"],
    secret_key=config["ALPACA_SECRET_KEY"]
)

# Set up logging for the entire backend
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG if you want more detailed output
    format='[%(asctime)s] %(levelname)s in %(name)s: %(message)s'
)

# This will hold the shared event loop
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

    # Start Alpaca streaming loop in background thread
    threading.Thread(target=start_alpaca_event_loop, daemon=True).start()

    # Register routes and events
    from .routes import main_bp
    from .socketio_events import register_socket_events

    app.register_blueprint(main_bp)
    register_socket_events(socketio)

    return app

if __name__ == "__main__":
    app = create_app()
    print("🚀 Starting Momo Bot backend via __main__.py...")
    try:
        socketio.run(app, host="0.0.0.0", port=5050)
    except Exception as e:
        print(f"🔥 Server error: {e}")