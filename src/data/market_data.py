import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from src.data.store import DataStore

class MarketDataFetcher:
    def __init__(self):
        self.store = DataStore()

    def fetch_data(self, ticker: str, period="5y", force_download=False) -> pd.DataFrame:
        """
        Fetches data from DB first, then updates from API if needed.
        force_download: If True, skips cache check and downloads fresh data.
        """
        if force_download:
             print(f"Forcing download for {ticker}...")
             last_date = None # Bypass cache check logic
        else:
             # Check latest date in DB
             last_date = self.store.get_latest_date(ticker)
        
        today = datetime.now().strftime('%Y-%m-%d')

        if last_date == today:
            # Check if we should force refresh (Trading Session Logic)
            # If it's a weekday, we assume market might be open or data changed intraday.
            # Simple check: If date == today, fetch the single day again to update Close price.
            is_weekend = datetime.now().weekday() >= 5
            if is_weekend:
                 # Market closed, cache is valid
                 print(f"Loading {ticker} from cache (Weekend)...")
                 return self.store.get_market_data(ticker)
            
            # If weekday, we force a refresh for today's data candle
            print(f"Intraday/Trading Session: Refreshing {ticker} for today...")
            start_date = today
        
        # Need to fetch new data
        start_date = None
        if last_date:
            start_dt = datetime.strptime(last_date, '%Y-%m-%d') + timedelta(days=1)
            if start_dt > datetime.now():
                # Already up to date (weekend case)
                return self.store.get_market_data(ticker)
            start_date = start_dt.strftime('%Y-%m-%d')
            print(f"Updating {ticker} from {start_date}...")
            
            # Fetch only missing range
            df = yf.download(ticker, start=start_date, progress=False)
        else:
            print(f"Downloading full history for {ticker}...")
            df = yf.download(ticker, period=period, progress=False)

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
            df = yf.download(ticker, period=period, interval=interval, prepost=True, progress=False)
            
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                
                # Standardize columns
                df.columns = [c.lower() for c in df.columns]
                return df
                
        except Exception as e:
            print(f"Error fetching intraday for {ticker}: {e}")
            
        return pd.DataFrame()
