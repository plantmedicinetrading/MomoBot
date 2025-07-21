# app/__main__.py

from . import create_app, socketio
import logging

if __name__ == "__main__":
    app = create_app()
    print("🚀 Starting Momo Bot backend via __main__.py...")
    try:
        socketio.run(app, host="0.0.0.0", port=5050)
    except Exception as e:
        logging.exception("🔥 Server error:")