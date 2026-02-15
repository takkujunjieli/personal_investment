import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, date
from src.data.store import DataStore

class MarketDataFetcher:
    def __init__(self):
        self.store = DataStore()

    def fetch_data(self, ticker: str, period="5y", force_download=False) -> pd.DataFrame:
        """
        Fetches data from DB first, then updates from API if needed.
        force_download: If True, skips cache check and downloads fresh data.
        """
        today_date = datetime.now().date()
        today_str = today_date.strftime('%Y-%m-%d')

        # Logic: We only sync COMPLETED days (up to yesterday).
        # If last_date >= yesterday, we are up to date.
        
        should_fetch = False
        if force_download:
             print(f"Forcing download for {ticker}...")
             start_date = None 
             should_fetch = True
        else:
             # Check latest date in DB
             last_date = self.store.get_latest_date(ticker)
             
             if not last_date:
                 should_fetch = True
                 start_date = None
             else:
                 last_dt = datetime.strptime(last_date, '%Y-%m-%d').date()
                 # If last data point is yesterday or later (today), we are good.
                 if last_dt >= (today_date - timedelta(days=1)):
                     # Already up to date (we have yesterday's close)
                     return self.store.get_market_data(ticker)
                 
                 start_date = (last_dt + timedelta(days=1)).strftime('%Y-%m-%d')
                 should_fetch = True

        if should_fetch:
            if start_date:
                print(f"Updating {ticker} from {start_date} to {today_str} (excluding today)...")
                try:
                    # Attempt incremental update with timeout and NO threads
                    # end=today_str means up to yesterday (exclusive of today)
                    df = yf.download(ticker, start=start_date, end=today_str, progress=False, timeout=10, threads=False)
                except Exception as e:
                    print(f"Incremental update failed/timed out for {ticker}: {e}. Retrying full history...")
                    df = pd.DataFrame() 

                if df.empty:
                     # Fallback to full download BUT still up to yesterday? 
                     # Or full download naturally includes today? 
                     # Let's effectively cap it at yesterday to be safe.
                     print(f"Incremental update returned empty/failed for {ticker}. Redownloading full history...")
                     df = yf.download(ticker, period=period, end=today_str, progress=False, timeout=20, threads=False)

            else:
                print(f"Downloading full history for {ticker} up to {today_str}...")
                df = yf.download(ticker, period=period, end=today_str, progress=False, timeout=20, threads=False)

            if not df.empty:
                # yfinance returns MultiIndex columns sometimes, flat it
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                
                # Save to DB
                self.store.save_market_data(ticker, df)
        
        # Return full dataset from DB to ensure consistency
        return self.store.get_market_data(ticker)

    def get_price(self, ticker: str):
        df = self.fetch_data(ticker)
        if not df.empty:
            return df['close'].iloc[-1]
        return None

    def fetch_intraday(self, ticker: str, period="5d", interval="5m") -> pd.DataFrame:
        """
        Fetches intraday data including Pre and Post market sessions.
        Note: Caching intraday data in the same way might be too heavy for SQLite. 
        For now, we will fetch live for the specific analysis and maybe cache recent ones.
        """
        print(f"Fetching intraday data for {ticker} ({period}, {interval})...")
        try:
            # prepost=True gives us the pre-market and after-hours action
            df = yf.download(ticker, period=period, interval=interval, prepost=True, progress=False, timeout=10, threads=False)
            
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                
                # Standardize columns
                df.columns = [c.lower() for c in df.columns]
                return df
                
        except Exception as e:
            print(f"Error fetching intraday for {ticker}: {e}")
            
        return pd.DataFrame()
