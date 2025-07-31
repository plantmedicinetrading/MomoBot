# app/test_hotkey.py

import asyncio
import sys
import os

# Add the parent directory to the path so we can import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.hotkey_utils import send_hotkey, send_hotkey_sequence

async def test_hotkey_functionality():
    """Test the hotkey functionality"""
    print("Testing WebSocket hotkey functionality...")
    
    # Test single hotkey
    print("\n1. Testing single hotkey 'buy_ask'...")
    success = await send_hotkey("buy_ask")
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    
    # Test hotkey sequence
    print("\n2. Testing hotkey sequence for TP1...")
    success = await send_hotkey_sequence(["sell_ask", "cancel_all", "break_even"])
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    
    # Test other hotkeys
    print("\n3. Testing 'sell_ask' hotkey...")
    success = await send_hotkey("sell_ask")
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    
    print("\n4. Testing 'sell_all_bid' hotkey...")
    success = await send_hotkey("sell_all_bid")
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    
    print("\nHotkey testing completed!")

if __name__ == "__main__":
    asyncio.run(test_hotkey_functionality()) 