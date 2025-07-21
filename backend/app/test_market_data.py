import asyncio
from alpaca.data.live import StockDataStream
from alpaca.data.models import Quote
from alpaca.data.enums import DataFeed
from dotenv import load_dotenv
import os

load_dotenv()  # Load from .env

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
FEED = os.getenv("ALPACA_FEED", "sip")  # Use "sip" for paper

stream = StockDataStream(API_KEY, SECRET_KEY, feed=DataFeed(FEED))

async def handle_quote(quote: Quote):
    print(f"💬 Quote received: {quote.symbol} | bid: {quote.bid_price}, ask: {quote.ask_price}")

async def main():
    symbol = "AAPL"
    print(f"🔌 Subscribing to quotes for {symbol} using feed={FEED}")
    stream.subscribe_quotes(handle_quote, symbol)
    await stream._run_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Interrupted by user")