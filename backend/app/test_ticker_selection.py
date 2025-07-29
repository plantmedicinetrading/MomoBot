#!/usr/bin/env python3
"""
Test script to simulate ticker selection and test historical data preloading.
"""

import sys
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ticker_selection():
    """Test the ticker selection and historical data preloading"""
    
    try:
        # Import the necessary modules
        from trading.stream.polygon_stream import preload_historical_data
        from shared_state import ticker_states
        
        # Test with a symbol
        symbol = "AAPL"
        print(f"\n{'='*50}")
        print(f"Testing ticker selection for {symbol}")
        print(f"{'='*50}")
        
        # Simulate ticker selection
        print(f"📊 Selecting ticker: {symbol}")
        
        # Preload historical data
        print(f"🔄 Preloading historical data for {symbol}...")
        historical_candles = preload_historical_data(symbol, hours_back=1)
        
        print(f"✅ Historical data preloaded:")
        print(f"   📈 10s candles: {len(historical_candles.get('10s', []))}")
        print(f"   📈 1m candles: {len(historical_candles.get('1m', []))}")
        print(f"   📈 5m candles: {len(historical_candles.get('5m', []))}")
        
        # Check if data was stored in ticker_states
        if symbol in ticker_states:
            state = ticker_states[symbol]
            print(f"📊 State data:")
            print(f"   📈 10s candles in state: {len(state.get('candles_10s', []))}")
            print(f"   📈 1m candles in state: {len(state.get('candles', []))}")
            print(f"   📈 5m candles in state: {len(state.get('candles_5m', []))}")
            
            # Show sample candles
            if state.get('candles'):
                print(f"\n📊 Sample 1m candle: {state['candles'][0] if state['candles'] else 'None'}")
            if state.get('candles_10s'):
                print(f"📊 Sample 10s candle: {state['candles_10s'][0] if state['candles_10s'] else 'None'}")
            if state.get('candles_5m'):
                print(f"📊 Sample 5m candle: {state['candles_5m'][0] if state['candles_5m'] else 'None'}")
        else:
            print(f"❌ No state found for {symbol}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing ticker selection: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing Ticker Selection and Historical Data Preloading")
    print("Make sure POLYGON_API_KEY is set in your environment")
    
    if not os.getenv("POLYGON_API_KEY"):
        print("❌ POLYGON_API_KEY not found in environment variables")
        print("Please set your Polygon API key:")
        print("export POLYGON_API_KEY='your_api_key_here'")
        sys.exit(1)
    
    success = test_ticker_selection()
    if success:
        print("\n✅ Ticker selection test completed successfully!")
    else:
        print("\n❌ Ticker selection test failed!")
        sys.exit(1) 