#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import socketio
import time
import json

def test_breakout_fix():
    """Test that breakout_ready is set and entry types work"""
    
    sio = socketio.Client()
    
    @sio.event
    def connect():
        print("✅ Connected to server")
        
    @sio.event
    def disconnect():
        print("❌ Disconnected from server")
        
    @sio.event
    def ticker_selected(data):
        print(f"📊 Ticker selected: {data}")
        
    @sio.event
    def entry_type_set(data):
        print(f"🔧 Entry type set: {data}")
        
    @sio.event
    def candle_update(data):
        print(f"🕯️ Candle update: {data.get('symbol')} {data.get('timeframe')} - {len(data.get('candles', []))} candles")
        
    @sio.event
    def error(data):
        print(f"❌ Error: {data}")
        
    try:
        # Connect to the server
        sio.connect('http://localhost:5050')
        
        # Wait a moment for connection
        time.sleep(1)
        
        # Select a ticker
        print("🔍 Selecting ticker AAPL...")
        sio.emit('select_ticker', {'ticker': 'AAPL'})
        
        # Wait for ticker selection
        time.sleep(2)
        
        # Set entry type to 10s
        print("🔧 Setting entry type to 10s...")
        sio.emit('set_entry_type', {'symbol': 'AAPL', 'entry_type': '10s'})
        
        # Wait for entry type to be set
        time.sleep(2)
        
        print("✅ Test completed. Check server logs for:")
        print("   - 'breakout_ready: True' message")
        print("   - Active entry type set to: 10s")
        print("   - Breakout logic should now work instead of 'Not ready' warnings")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
    finally:
        sio.disconnect()

if __name__ == "__main__":
    test_breakout_fix() 