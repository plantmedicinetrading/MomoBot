from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

@app.route("/")
def index():
    return {"message": "SocketIO test running"}

@socketio.on('connect')
def test_connect():
    print("✅ Client connected")

@socketio.on('disconnect')
def test_disconnect():
    print("❌ Client disconnected")

@socketio.on('select_ticker')
def handle_ticker(ticker):
    print(f"📩 Ticker received: {ticker}")
    socketio.emit('ticker_selected', {'ticker': ticker})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5050)