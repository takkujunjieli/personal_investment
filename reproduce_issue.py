from src.data.market_data import MarketDataFetcher
import yfinance as yf
from datetime import datetime

print("Starting reproduction script...")
ticker = "LHX"
start_date = "2026-02-11"

print(f"Testing direct yfinance download for {ticker} from {start_date}...")
try:
    df = yf.download(ticker, start=start_date, progress=False)
    print("Download finished.")
    print(df)
except Exception as e:
    print(f"Download failed: {e}")

print("Testing MarketDataFetcher...")
fetcher = MarketDataFetcher()
# We need to simulate the state where it tries to update.
# But simply calling fetch_data should trigger the logic if we pass the right conditions or if the DB has the old date.
# However, we don't want to mess up the user's DB if possible, but fetch_data writes to DB.
# Let's just rely on the direct yfinance call first as that's the likely blocker.
