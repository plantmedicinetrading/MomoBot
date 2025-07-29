#!/usr/bin/env python3
"""
Direct test of historical data functionality.
"""

import sys
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_historical_data_direct():
    """Test the historical data functionality directly"""
    
    try:
        # Import the function directly
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Test the historical data function
        print("🧪 Testing Historical Data Functionality Directly")
        
        # Import the function
        from trading.stream.polygon_stream import preload_historical_data
        
        # Test with AAPL
        symbol = "AAPL"
        print(f"📊 Testing historical data for {symbol}")
        
        # Call the function
        historical_candles = preload_historical_data(symbol, hours_back=1)
        
        print(f"✅ Historical data retrieved:")
        print(f"   📈 10s candles: {len(historical_candles.get('10s', []))}")
        print(f"   📈 1m candles: {len(historical_candles.get('1m', []))}")
        print(f"   📈 5m candles: {len(historical_candles.get('5m', []))}")
        
        # Show sample data
        if historical_candles.get('1m'):
            print(f"📊 Sample 1m candle: {historical_candles['1m'][0]}")
        
        if historical_candles.get('10s'):
            print(f"📊 Sample 10s candle: {historical_candles['10s'][0]}")
        
        if historical_candles.get('5m'):
            print(f"📊 Sample 5m candle: {historical_candles['5m'][0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing historical data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Direct Historical Data Test")
    print("Make sure POLYGON_API_KEY is set in your environment")
    
    if not os.getenv("POLYGON_API_KEY"):
        print("❌ POLYGON_API_KEY not found in environment variables")
        print("Please set your Polygon API key:")
        print("export POLYGON_API_KEY='your_api_key_here'")
        sys.exit(1)
    
    success = test_historical_data_direct()
    if success:
        print("\n✅ Historical data test completed successfully!")
    else:
        print("\n❌ Historical data test failed!")
        sys.exit(1) 