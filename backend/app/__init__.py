from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

# Global SocketIO instance
socketio = SocketIO(cors_allowed_origins="*", async_mode='gevent')

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Initialize SocketIO with the app
    socketio.init_app(app)

    # Register routes and socket events
    from .routes import main_bp
    from .socketio_events import register_socket_events

    app.register_blueprint(main_bp)
    register_socket_events(socketio)

    return app

# 🔥 Run server if this file is executed as a script with `-m`
if __name__ == '__main__':
    app = create_app()
    print("🚀 Starting Momo Bot backend...")
    try:
        socketio.run(app, host='0.0.0.0', port=5050)
    except Exception as e:
        print(f"🔥 Server error: {e}")