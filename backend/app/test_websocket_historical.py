#!/usr/bin/env python3
"""
Test script to simulate WebSocket connection and test historical data preloading.
"""

import socketio
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_websocket_historical_data():
    """Test the WebSocket connection and historical data preloading"""
    
    # Create a Socket.IO client
    sio = socketio.Client()
    
    # Track events
    events_received = []
    
    @sio.event
    def connect():
        logger.info("✅ Connected to server")
        events_received.append("connected")
        
        # Select a ticker to trigger historical data preloading
        logger.info("📊 Selecting ticker: AAPL")
        sio.emit('select_ticker', {'ticker': 'AAPL'})
    
    @sio.event
    def disconnect():
        logger.info("❌ Disconnected from server")
        events_received.append("disconnected")
    
    @sio.on('candle_update')
    def on_candle_update(data):
        logger.info(f"📊 Received candle update: {data}")
        events_received.append("candle_update")
        
        # Check if this is historical data
        if data.get('is_historical'):
            logger.info(f"📚 Received historical candles for {data.get('symbol')} ({data.get('timeframe')})")
            events_received.append("historical_candles")
            
            # Check the data structure
            if 'candles' in data:
                candles = data['candles']
                logger.info(f"📈 Received {len(candles)} historical candles")
                if candles:
                    logger.info(f"📊 Sample candle: {candles[0]}")
            
            # Disconnect after receiving historical data
            sio.disconnect()
        else:
            logger.info(f"📊 Received real-time candle update for {data.get('symbol')} ({data.get('timeframe')})")
    
    @sio.on('ticker_selected')
    def on_ticker_selected(data):
        logger.info(f"📊 Ticker selected: {data}")
        events_received.append("ticker_selected")
    
    @sio.on('error')
    def on_error(data):
        logger.error(f"❌ Server error: {data}")
        events_received.append("error")
    
    @sio.on('connect_error')
    def on_connect_error(data):
        logger.error(f"❌ Connection error: {data}")
        events_received.append("connect_error")
    
    try:
        # Connect to the server
        logger.info("🔄 Connecting to server at http://localhost:5050")
        sio.connect('http://localhost:5050')
        
        # Wait for events
        timeout = 30
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if "historical_candles" in events_received:
                logger.info("✅ Successfully received historical candles!")
                break
            time.sleep(0.1)
        
        if "historical_candles" not in events_received:
            logger.warning("⚠️ Did not receive historical candles within timeout")
            logger.info(f"Events received: {events_received}")
        
        return "historical_candles" in events_received
        
    except Exception as e:
        logger.error(f"❌ Error during test: {e}")
        return False
    
    finally:
        if sio.connected:
            sio.disconnect()

if __name__ == "__main__":
    print("🧪 Testing WebSocket Historical Data Preloading")
    print("Make sure the server is running on port 5050")
    
    success = test_websocket_historical_data()
    
    if success:
        print("\n✅ WebSocket historical data test completed successfully!")
    else:
        print("\n❌ WebSocket historical data test failed!")
        exit(1) 