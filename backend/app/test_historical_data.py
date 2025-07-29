#!/usr/bin/env python3
"""
Test script for historical data preloading functionality.
Run this to test the Polygon Quote API integration.
"""

import sys
import os
import logging
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pytz

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_historical_quotes_direct(symbol: str, hours_back: int = 1, limit: int = 50000):
    """
    Fetch historical quote data from Polygon Quote API directly.
    """
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise ValueError('POLYGON_API_KEY not set')
    
    # Calculate timestamp for hours_back in ET timezone
    et_tz = pytz.timezone('US/Eastern')
    end_time = datetime.now(et_tz)
    start_time = end_time - timedelta(hours=hours_back)
    
    # Format timestamps in ISO format for Polygon API
    start_timestamp = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_timestamp = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    url = f"https://api.polygon.io/v3/quotes/{symbol.upper()}"
    params = {
        'timestamp.gte': start_timestamp,
        'timestamp.lte': end_timestamp,
        'limit': min(limit, 50000),
        'apiKey': api_key
    }
    
    print(f"[Polygon] Fetching historical quotes for {symbol} from {start_time} to {end_time}")
    print(f"[Polygon] URL: {url}")
    print(f"[Polygon] Params: {params}")
    
    try:
        response = requests.get(url, params=params)
        print(f"[Polygon] Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[Polygon] Response text: {response.text}")
            response.raise_for_status()
            
        data = response.json()
        print(f"[Polygon] Response data keys: {list(data.keys())}")
        print(f"[Polygon] Results count: {len(data.get('results', []))}")
        
        # Debug: Show the structure of the first quote
        if data.get('results'):
            first_quote = data['results'][0]
            print(f"[Polygon] First quote structure: {first_quote}")
            print(f"[Polygon] First quote keys: {list(first_quote.keys())}")
        
        quotes = []
        for quote in data.get('results', []):
            # Convert nanoseconds to datetime using sip_timestamp
            timestamp = datetime.fromtimestamp(quote['sip_timestamp'] / 1_000_000_000)
            
            quote_data = {
                'timestamp': timestamp,
                'ask_price': quote.get('ask_price'),
                'bid_price': quote.get('bid_price'),
                'ask_size': quote.get('ask_size', 0),
                'bid_size': quote.get('bid_size', 0)
            }
            quotes.append(quote_data)
        
        print(f"[Polygon] Fetched {len(quotes)} historical quotes for {symbol}")
        return quotes
        
    except requests.exceptions.RequestException as e:
        print(f"[Polygon] Error fetching historical quotes for {symbol}: {e}")
        raise

def fetch_historical_aggregates_direct(symbol: str, hours_back: int = 1):
    """
    Fetch historical aggregated bars from Polygon API as an alternative to quotes.
    """
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise ValueError('POLYGON_API_KEY not set')
    
    # Calculate timestamp for hours_back
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours_back)
    
    # Convert to milliseconds (Polygon aggregates API expects milliseconds)
    start_timestamp = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)
    
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol.upper()}/range/1/minute/{start_timestamp}/{end_timestamp}"
    params = {
        'adjusted': 'true',
        'sort': 'asc',
        'limit': 50000,
        'apiKey': api_key
    }
    
    print(f"[Polygon] Fetching historical aggregates for {symbol} from {start_time} to {end_time}")
    print(f"[Polygon] URL: {url}")
    
    try:
        response = requests.get(url, params=params)
        print(f"[Polygon] Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[Polygon] Response text: {response.text}")
            response.raise_for_status()
            
        data = response.json()
        print(f"[Polygon] Response data keys: {list(data.keys())}")
        print(f"[Polygon] Results count: {len(data.get('results', []))}")
        
        bars = []
        for bar in data.get('results', []):
            # Convert milliseconds to datetime
            timestamp = datetime.fromtimestamp(bar['t'] / 1000)
            
            bar_data = {
                'timestamp': timestamp,
                'open': bar['o'],
                'high': bar['h'],
                'low': bar['l'],
                'close': bar['c'],
                'volume': bar['v']
            }
            bars.append(bar_data)
        
        print(f"[Polygon] Fetched {len(bars)} historical bars for {symbol}")
        return bars
        
    except requests.exceptions.RequestException as e:
        print(f"[Polygon] Error fetching historical aggregates for {symbol}: {e}")
        raise

def test_historical_data():
    """Test the historical data preloading functionality"""
    
    # Test symbols (use liquid stocks that are likely to have quote data)
    test_symbols = ["AAPL", "MSFT", "TSLA", "SBET"]
    
    # Test different time ranges
    time_ranges = [1, 6, 24]  # 1 hour, 6 hours, 24 hours
    
    for symbol in test_symbols:
        print(f"\n{'='*50}")
        print(f"Testing historical data for {symbol}")
        print(f"{'='*50}")
        
        for hours_back in time_ranges:
            print(f"\n--- Testing {hours_back} hour(s) back ---")
            
            try:
                # Fetch historical quotes directly
                quotes = fetch_historical_quotes_direct(symbol, hours_back=hours_back)
                
                if quotes:
                    print(f"✅ Successfully fetched {len(quotes)} quotes for {symbol} ({hours_back}h back)")
                    
                    # Show sample quotes
                    print(f"\nSample quotes:")
                    for i, quote in enumerate(quotes[:3]):  # Show first 3 quotes
                        print(f"  Quote {i+1}: {quote}")
                    
                    # Analyze quote distribution
                    timestamps = [q['timestamp'] for q in quotes]
                    if timestamps:
                        print(f"\nTime range: {min(timestamps)} to {max(timestamps)}")
                        print(f"Total time span: {max(timestamps) - min(timestamps)}")
                    
                    # Check for price data
                    prices = []
                    for quote in quotes:
                        if quote['ask_price']:
                            prices.append(quote['ask_price'])
                        if quote['bid_price']:
                            prices.append(quote['bid_price'])
                    
                    if prices:
                        print(f"Price range: ${min(prices):.2f} - ${max(prices):.2f}")
                        print(f"Average price: ${sum(prices)/len(prices):.2f}")
                    
                    # If we found data, break out of the time range loop
                    break
                    
                else:
                    print(f"⚠️ No quotes found for {symbol} ({hours_back}h back)")
                    
            except Exception as e:
                print(f"❌ Error testing {symbol} ({hours_back}h back): {e}")
                logger.exception(f"Error testing {symbol}")

if __name__ == "__main__":
    print("🧪 Testing Historical Data Preloading")
    print("Make sure POLYGON_API_KEY is set in your environment")
    
    if not os.getenv("POLYGON_API_KEY"):
        print("❌ POLYGON_API_KEY not found in environment variables")
        print("Please set your Polygon API key:")
        print("export POLYGON_API_KEY='your_api_key_here'")
        sys.exit(1)
    
    test_historical_data()
    print("\n✅ Historical data test completed!") 