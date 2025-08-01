# app/utils/voice_utils.py

import pyttsx3
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global engine instance
_engine = None
_lock = threading.Lock()

def get_engine():
    """Get or create the text-to-speech engine instance."""
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                try:
                    _engine = pyttsx3.init()
                    # Configure voice settings for robotic sound
                    voices = _engine.getProperty('voices')
                    if voices:
                        # Try to find a male voice (usually more robotic)
                        for voice in voices:
                            if 'male' in voice.name.lower() or 'david' in voice.name.lower():
                                _engine.setProperty('voice', voice.id)
                                break
                    
                    # Set speech rate and volume
                    _engine.setProperty('rate', 150)  # Speed of speech
                    _engine.setProperty('volume', 0.8)  # Volume level
                    
                    logger.info("[Voice] Text-to-speech engine initialized")
                except Exception as e:
                    logger.error(f"[Voice] Failed to initialize text-to-speech engine: {e}")
                    return None
    return _engine

def speak_announcement(text: str) -> None:
    """
    Speak a text announcement using text-to-speech.
    
    Args:
        text: The text to speak
    """
    def speak_in_thread():
        try:
            engine = get_engine()
            if engine:
                engine.say(text)
                engine.runAndWait()
                logger.info(f"[Voice] Spoke: {text}")
            else:
                logger.warning("[Voice] Text-to-speech engine not available")
        except Exception as e:
            logger.error(f"[Voice] Failed to speak announcement '{text}': {e}")
    
    # Run in a separate thread to avoid blocking
    thread = threading.Thread(target=speak_in_thread)
    thread.daemon = True
    thread.start()

def announce_new_trade(ticker: str, entry_price: float) -> None:
    """
    Announce a new trade with robotic voice.
    
    Args:
        ticker: The stock ticker symbol
        entry_price: The entry price of the trade
    """
    announcement = f"New trade taken for {ticker} at {entry_price:.2f}"
    speak_announcement(announcement)

def announce_trade_exit(ticker: str, exit_price: float, reason: str = "exit") -> None:
    """
    Announce a trade exit with robotic voice.
    
    Args:
        ticker: The stock ticker symbol
        exit_price: The exit price of the trade
        reason: The reason for exit (e.g., "take profit", "stop loss")
    """
    announcement = f"Trade closed for {ticker} at {exit_price:.2f} due to {reason}"
    speak_announcement(announcement) 