# app/state.py

import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# Container for tracking which trades are active
active_trades = {}

# Global config from .env
config = {
    "ALPACA_ENV": os.getenv("ALPACA_ENV", "paper"),
    "ALPACA_API_KEY": os.getenv("ALPACA_API_KEY"),
    "ALPACA_SECRET_KEY": os.getenv("ALPACA_SECRET_KEY"),
    "ALPACA_FEED": os.getenv("ALPACA_FEED", "sip"),
     "ALPACA_BASE_URL": os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
}

# Symbol-specific runtime state
ticker_states = defaultdict(lambda: {
    "active_entry_type": None,  # "10s", "1m", or "5m"
    "position": None,           # Active position info
    "1m": {},                   # 1-min entry state
    "10s": {},                  # 10-sec entry state
    "5m": {},                   # 5-min entry state
})

# Direct exports for convenience
ALPACA_API_KEY = config["ALPACA_API_KEY"]
ALPACA_SECRET_KEY = config["ALPACA_SECRET_KEY"]
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL")  # In case it's not included in config