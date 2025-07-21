import pandas as pd
from datetime import datetime
import pytz
import logging

logger = logging.getLogger(__name__)

class Candle:
    def __init__(self, timestamp, open, high, low, close, volume):
        self.timestamp = timestamp
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

class PullbackTracker:
    def __init__(self, symbol):
        self.symbol = symbol
        self.df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
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
            logger.info(f"🕒 Finalized candle for {self.symbol} at {formatted_time} → Close: {latest['close']}, High: {latest['high']}")
            self.last_logged_minute = latest_minute

        # Step 1: Detect pullback (close < previous close)
        if latest["close"] < prev["close"]:
            if not self.pullback_active:
                self.last_breakout_level = latest["high"]
                self.pullback_active = True
                self.breakout_triggered = False
                logger.info(f"🔍 New pullback started on {self.symbol} — breakout level set to {self.last_breakout_level}")
            else:
                if latest["high"] < self.last_breakout_level:
                    self.last_breakout_level = latest["high"]
                    logger.info(f"🔽 Lower high detected — adjusting breakout level for {self.symbol} to {self.last_breakout_level}")

        # Step 2: Even if not a new pullback, still check for lower highs
        elif self.pullback_active and not self.breakout_triggered:
            if latest["high"] < self.last_breakout_level:
                self.last_breakout_level = latest["high"]
                logger.info(f"🔽 Lower high detected — adjusting breakout level for {self.symbol} to {self.last_breakout_level}")

        # Step 3: Log active breakout level
        #if self.pullback_active and not self.breakout_triggered:
        # logger.info(f"📈 {self.symbol} breakout level still active: {self.last_breakout_level}")

    def check_tick_for_entry(self, price: float) -> bool:
        if self.last_breakout_level is None or self.breakout_triggered or not self.pullback_active:
            return False

        if price > self.last_breakout_level:
            self.breakout_triggered = True
            self.last_breakout_index = len(self.df) - 1
            self.pullback_active = False
            logger.info(f"✅ Tick breakout detected — price: {price}, breakout level: {self.last_breakout_level}")
            logger.info(f"🚀 Entry signal for {self.symbol} at ${price}!")
            return True

        return False