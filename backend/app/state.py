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