import pandas as pd
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

from ..core.execution import submit_order
from ..core.trade_manager import handle_breakout_trigger

def get_socketio():
    """Lazy import of socketio to avoid circular imports"""
    try:
        import sys
        app_module = sys.modules.get('backend.app')
        if app_module and hasattr(app_module, 'socketio'):
            return app_module.socketio
        return None
    except Exception as e:
        logger.warning(f"Could not get socketio: {e}")
        return None

class Candle:
    def __init__(self, timestamp, open, high, low, close, volume):
        self.timestamp = timestamp
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

class PullbackTracker:
    def __init__(self, symbol, interval="1m"):
        self.symbol = symbol
        self.interval = interval
        self.df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])  # type: ignore
        self.last_breakout_level = None
        self.breakout_triggered = False
        self.last_breakout_index = -1
        self.last_logged_minute = None
        self.pullback_active = False

    def add_candle(self, candle: Candle):
        new_row = {
            "timestamp": pd.to_datetime(candle.timestamp),
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume
        }

        if self.df.empty:
            self.df = pd.DataFrame([new_row])
        else:
            self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)

        self.df = self.df.tail(100)

        if len(self.df) < 2:
            return

        prev = self.df.iloc[-2]
        latest = self.df.iloc[-1]

        # 🕒 Log finalized candle in NY time
        latest_minute = latest["timestamp"].replace(second=0, microsecond=0)
        if latest_minute.tzinfo is None:
            latest_minute = latest_minute.tz_localize('UTC')
        ny_time = latest_minute.tz_convert('America/New_York')
        formatted_time = ny_time.strftime('%I:%M %p ET')

        if self.last_logged_minute != latest_minute:
            logger.info(f"🕒 Finalized {self.interval} candle for {self.symbol} at {formatted_time} → Close: {latest['close']}, High: {latest['high']}")
            self.last_logged_minute = latest_minute

        # Simple breakout level calculation:
        # If the HIGH of the previous candle is higher than the HIGH of the most recently closed candle,
        # then the new breakout level is set to the HIGH of the candle that has just closed.
        if prev["high"] > latest["high"]:
            self.last_breakout_level = latest["high"]
            self.pullback_active = True
            self.breakout_triggered = False
            logger.info(f"🔽 Lower high detected ({self.interval}) — adjusting breakout level for {self.symbol} to {self.last_breakout_level}")
            self.emit_breakout_levels()
        elif latest["high"] > prev["high"]:
            # Higher high detected - reset breakout level as pullback is over
            if self.last_breakout_level is not None:
                logger.info(f"📈 Higher high detected ({self.interval}) — resetting breakout level for {self.symbol}")
                self.last_breakout_level = None
                self.pullback_active = False
                self.breakout_triggered = False
                self.emit_breakout_levels()
        else:
            # If no lower high, maintain current breakout level if it exists
            # Don't reset pullback_active here - keep the breakout level active
            if self.last_breakout_level is not None:
                self.emit_breakout_levels()

    def check_tick_for_entry(self, symbol: str, price: float, bid=None, ask=None) -> bool:
        from ...shared_state import ticker_states
        state = ticker_states.get(symbol)
        # Only emit/trigger breakouts if this tracker's interval matches the active_entry_type
        if state is not None and state.get("active_entry_type") != self.interval:
            # Still update state, but do not emit entry signals
            return False
        if self.last_breakout_level is None or self.breakout_triggered or not self.pullback_active:
            return False

        if price > self.last_breakout_level:
            self.breakout_triggered = True
            self.last_breakout_index = len(self.df) - 1
            self.pullback_active = False
            logger.info(f"✅ Tick breakout detected — price: {price}, breakout level: {self.last_breakout_level}")
            logger.info(f"🚀 Entry signal for {self.symbol} at ${price}!")
            
           

            # Define a basic size for now — later you’ll parameterize this
            position_size = 1000  # or dynamically fetched

            # Submit the order
            if bid is None or ask is None:
                return False  # or handle as appropriate

            from ..core.trade_manager import handle_breakout_trigger
            handle_breakout_trigger(symbol, price, self.interval, bid, ask)

            
            return True

        return False

    def emit_breakout_levels(self):
        """Emit current breakout levels to frontend"""
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
                logger.info(f"📊 {self.symbol} {interval} breakout level: {tracker.last_breakout_level}")
            else:
                levels.append(None)
                logger.info(f"📊 {self.symbol} {interval} breakout level: None (level: {tracker.last_breakout_level if tracker else None}, triggered: {tracker.breakout_triggered if tracker else False})")
        
        # Emit to frontend
        socketio = get_socketio()
        if socketio:
            logger.info(f"📡 Emitting breakout levels for {self.symbol}: {levels}")
            socketio.emit('breakout_levels', {
                'symbol': self.symbol,
                'levels': levels
            })
        else:
            logger.warning(f"socketio not available, cannot emit breakout levels for {self.symbol}")
