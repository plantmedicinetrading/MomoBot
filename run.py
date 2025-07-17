from backend.app import create_app

app = create_app()

from backend.app import socketio  # Import after app creation

if __name__ == '__main__':
    print("🚀 Starting Momo Bot backend...")
    socketio.run(app, host='0.0.0.0', port=5050)

try:
    socketio.run(app, host='0.0.0.0', port=5050)
except Exception as e:
    print(f"🔥 Server error: {e}")