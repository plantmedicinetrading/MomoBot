# app/__main__.py

import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)

from . import create_app, socketio
import logging

if __name__ == "__main__":
    from .db import init_db
    init_db()
    app = create_app()
    print("🚀 Starting Momo Bot backend via __main__.py...")
    try:
        socketio.run(app, host="0.0.0.0", port=5050)
    except Exception as e:
        logging.exception("🔥 Server error:")