from src.engines.market_timing_engine import MarketTimingEngine
import pandas as pd

print("Testing PEAD Scan (Daily Refactor)...")
engine = MarketTimingEngine()

# Test with a known list of tickers, or just a few common ones
tickers = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT"]

print(f"Scanning {tickers}...")
try:
    df = engine.scan_pead(tickers)
    print("Scan complete.")
    if not df.empty:
        print("Candidates found:")
        print(df)
    else:
        print("No candidates found (expected if no gaps today).")
except Exception as e:
    print(f"Error during scan: {e}")
