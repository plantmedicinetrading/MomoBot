from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*", async_mode='gevent')  # declared globally

def create_app():
    app = Flask(__name__)
    CORS(app)

    # ✅ Properly initialize socketio with Flask app
    socketio.init_app(app)

    from .routes import main_bp
    from .socketio_events import register_socket_events

    app.register_blueprint(main_bp)
    register_socket_events(socketio)

    return app