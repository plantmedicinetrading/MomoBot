#!/usr/bin/env python3
# test_voice.py

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.voice_utils import announce_new_trade, announce_trade_exit, speak_announcement
import time

def test_voice_announcements():
    """Test the voice announcement functionality."""
    print("Testing voice announcements...")
    
    # Test basic text-to-speech
    print("1. Testing basic text-to-speech...")
    speak_announcement("Voice system initialized and ready for trading")
    time.sleep(2)
    
    # Test new trade announcement
    print("2. Testing new trade announcement...")
    announce_new_trade("AAPL", 150.25)
    time.sleep(2)
    
    # Test trade exit announcements
    print("3. Testing trade exit announcements...")
    announce_trade_exit("AAPL", 155.50, "take profit one")
    time.sleep(2)
    
    announce_trade_exit("TSLA", 240.75, "take profit two")
    time.sleep(2)
    
    announce_trade_exit("NVDA", 145.20, "stop loss")
    time.sleep(2)
    
    announce_trade_exit("MSFT", 320.10, "manual close")
    time.sleep(2)
    
    print("Voice announcement tests completed!")

if __name__ == "__main__":
    test_voice_announcements() 