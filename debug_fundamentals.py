import yfinance as yf
import pandas as pd

def debug_ticker(ticker_symbol):
    print(f"--- Debugging {ticker_symbol} ---")
    ticker = yf.Ticker(ticker_symbol)
    
    print("1. Fetching quarterly_financials...")
    try:
        qfin = ticker.quarterly_financials
        if qfin.empty:
            print("   [!] Empty DataFrame")
        else:
            print(f"   [OK] Shape: {qfin.shape}")
            print("   Index (First 5):")
            print(qfin.index[:5].tolist())
            if 'Net Income' in qfin.index:
                print(f"   Net Income (Last 3): {qfin.loc['Net Income'].head(3).tolist()}")
            else:
                print("   [!] 'Net Income' NOT FOUND in index.")
    except Exception as e:
        print(f"   [!] Error: {e}")

    print("\n2. Fetching quarterly_balance_sheet...")
    try:
        qbs = ticker.quarterly_balance_sheet
        if qbs.empty:
            print("   [!] Empty DataFrame")
        else:
            print(f"   [OK] Shape: {qbs.shape}")
            if 'Stockholders Equity' in qbs.index:
                print(f"   Stockholders Equity (Last 3): {qbs.loc['Stockholders Equity'].head(3).tolist()}")
            else:
                print("   [!] 'Stockholders Equity' NOT FOUND in index.")
    except Exception as e:
        print(f"   [!] Error: {e}")

if __name__ == "__main__":
    debug_ticker("AAPL")
    debug_ticker("MSFT")
