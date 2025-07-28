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

        # Step 1: Detect pullback (close < previous close)
        if latest["close"] < prev["close"]:
            if not self.pullback_active:
                # Start new pullback sequence
                self.last_breakout_level = latest["high"]
                self.pullback_active = True
                self.breakout_triggered = False
                logger.info(f"🔍 New pullback started on {self.symbol} ({self.interval}) — breakout level set to {self.last_breakout_level}")
                self.emit_breakout_levels()
            else:
                # Already in a pullback, check for lower high
                if latest["high"] < self.last_breakout_level:
                    self.last_breakout_level = latest["high"]
                    logger.info(f"🔽 Lower high detected ({self.interval}) — adjusting breakout level for {self.symbol} to {self.last_breakout_level}")
                    self.emit_breakout_levels()
                else:
                    logger.debug(f"📈 {self.symbol} ({self.interval}) — high {latest['high']} >= breakout level {self.last_breakout_level}")

        # Step 2: Check for lower highs even when not in a pullback (close >= previous close)
        elif latest["high"] < prev["high"]:
            # Lower high detected - this should always update the breakout level
            if not self.pullback_active:
                # Start new pullback sequence
                self.last_breakout_level = latest["high"]
                self.pullback_active = True
                self.breakout_triggered = False
                logger.info(f"🔍 New pullback started on {self.symbol} ({self.interval}) — breakout level set to {self.last_breakout_level} (lower high)")
                self.emit_breakout_levels()
            else:
                # Already in a pullback, update to this lower high
                self.last_breakout_level = latest["high"]
                logger.info(f"🔽 Lower high detected ({self.interval}) — adjusting breakout level for {self.symbol} to {self.last_breakout_level}")
                self.emit_breakout_levels()

        # Step 3: Check for continuation of existing pullback (even if not a new pullback candle)
        elif self.pullback_active and not self.breakout_triggered:
            if latest["high"] < self.last_breakout_level:
                self.last_breakout_level = latest["high"]
                logger.info(f"🔽 Lower high detected ({self.interval}) — adjusting breakout level for {self.symbol} to {self.last_breakout_level}")
                self.emit_breakout_levels()
            else:
                logger.debug(f"📈 {self.symbol} ({self.interval}) — high {latest['high']} >= breakout level {self.last_breakout_level}")
                # Emit current levels even if no change, so frontend gets updates
                self.emit_breakout_levels()

        # Step 4: Reset pullback state if we've had a strong move up (potential new trend)
        elif self.pullback_active and not self.breakout_triggered and latest["close"] > prev["high"]:
            # If we have a strong upward move (close > previous high), reset pullback state
            logger.info(f"🔄 Strong upward move detected ({self.interval}) — resetting pullback state for {self.symbol}")
            self.pullback_active = False
            self.last_breakout_level = None
            self.breakout_triggered = False
            self.emit_breakout_levels()

        # Step 5: If we have an active breakout level, emit it periodically
        elif self.pullback_active and not self.breakout_triggered and self.last_breakout_level is not None:
            logger.debug(f"📊 {self.symbol} ({self.interval}) — maintaining breakout level {self.last_breakout_level}")
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
            if tracker and tracker.pullback_active and not tracker.breakout_triggered:
                levels.append(tracker.last_breakout_level)
                logger.info(f"📊 {self.symbol} {interval} breakout level: {tracker.last_breakout_level}")
            else:
                levels.append(None)
                logger.info(f"📊 {self.symbol} {interval} breakout level: None (active: {tracker.pullback_active if tracker else False}, triggered: {tracker.breakout_triggered if tracker else False})")
        
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
