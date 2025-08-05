import logging
from typing import Optional

logger = logging.getLogger(__name__)

class CustomLevelEntry:
    def __init__(self, symbol: str, custom_level: float = None):
        self.symbol = symbol
        self.custom_level = custom_level
        self.entry_triggered = False
        if custom_level is not None:
            logger.info(f"[CUSTOM-LEVEL] Created custom level entry for {symbol} at ${custom_level:.2f}")
        else:
            logger.info(f"[CUSTOM-LEVEL] Created custom level entry for {symbol} with no level set")
    
    def check_tick_for_entry(self, symbol: str, price: float, bid: float, ask: float) -> bool:
        """
        Check if the current tick should trigger an entry at the custom level.
        Returns True if entry should be triggered.
        """
        if self.entry_triggered or self.custom_level is None:
            return False
        
        # Check if price crosses above the custom level
        if price >= self.custom_level:
            logger.info(f"[CUSTOM-LEVEL] {symbol} price {price:.2f} >= custom level {self.custom_level:.2f} - triggering entry")
            self.entry_triggered = True
            return True
        
        return False
    
    def reset(self):
        """Reset the entry trigger state"""
        self.entry_triggered = False
        logger.info(f"[CUSTOM-LEVEL] Reset entry trigger for {self.symbol}")
    
    def update_level(self, new_level: float):
        """Update the custom level and reset trigger state"""
        self.custom_level = new_level
        self.entry_triggered = False
        if new_level is not None:
            logger.info(f"[CUSTOM-LEVEL] Updated custom level for {self.symbol} to ${new_level:.2f}")
        else:
            logger.info(f"[CUSTOM-LEVEL] Cleared custom level for {self.symbol}")
        
        # Emit updated breakout levels to frontend
        self.emit_breakout_levels()
    
    def emit_breakout_levels(self):
        """Emit current breakout levels including custom level"""
        from ...shared_state import ticker_states
        state = ticker_states.get(self.symbol)
        if state is None:
            logger.warning(f"No state found for {self.symbol}")
            return
            
        # Get all trackers for this symbol
        trackers = {
            '10s': state.get('pullback_tracker_10s'),
            '1m': state.get('pullback_tracker_1m'),
            '5m': state.get('pullback_tracker_5m')
        }
        
        # Collect breakout levels
        levels = []
        for interval in ['10s', '1m', '5m']:
            tracker = trackers.get(interval)
            if tracker and tracker.last_breakout_level is not None and not tracker.breakout_triggered:
                levels.append(tracker.last_breakout_level)
            else:
                levels.append(None)
        
        # Add custom level
        if self.custom_level is not None and not self.entry_triggered:
            levels.append(self.custom_level)
            logger.info(f"📊 {self.symbol} custom breakout level: {self.custom_level}")
        else:
            levels.append(None)
            logger.info(f"📊 {self.symbol} custom breakout level: None")
        
        # Emit to frontend
        try:
            import sys
            app_module = sys.modules.get('backend.app')
            if app_module and hasattr(app_module, 'socketio'):
                socketio = app_module.socketio
                logger.info(f"📡 Emitting breakout levels for {self.symbol}: {levels}")
                socketio.emit('breakout_levels', {
                    'symbol': self.symbol,
                    'levels': levels
                })
            else:
                logger.warning(f"socketio not available, cannot emit breakout levels for {self.symbol}")
        except Exception as e:
            logger.warning(f"Failed to emit breakout levels: {e}") 