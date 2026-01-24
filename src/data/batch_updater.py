import yfinance as yf
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.data.store import DataStore
from src.data.fundamental_data import FundamentalDataFetcher

class BatchUpdater:
    def __init__(self):
        self.store = DataStore()
        self.fund_fetcher = FundamentalDataFetcher()

    def update_price_history(self, tickers: list):
        """
        Batch downloads price history for all tickers efficiently.
        """
        print(f"Batch Syncing Prices for {len(tickers)} tickers...")
        # yfinance bulk download
        # Use period="2y" to cover all strategy needs
        # group_by='ticker' makes it easier to iterate
        try:
            data = yf.download(tickers, period="2y", group_by='ticker', threads=True, progress=False)
            
            # If single ticker, structure is different (just DataFrame), if multiple, MultiIndex columns
            if len(tickers) == 1:
                # Handle single ticker case manually or wrap content
                ticker = tickers[0]
                if not data.empty:
                    self.store.save_market_data(ticker, data)
            else:
                # Multi-ticker
                for ticker in tickers:
                    try:
                        df = data[ticker]
                        if not df.empty:
                            # Drop rows with all NaNs (common in bulk download)
                            df = df.dropna(how='all')
                            if not df.empty:
                                self.store.save_market_data(ticker, df)
                    except KeyError:
                        continue
                        
            print("Price Sync Complete.")
        except Exception as e:
            print(f"Batch Price Sync Error: {e}")

    def update_fundamentals_and_info(self, tickers: list, max_workers=5):
        """
        Updates Fundamentals (Financials) AND Snapshot Info (PEG, Sector) concurrently.
        """
        print(f"Batch Syncing Fundamentals for {len(tickers)} tickers (Workers={max_workers})...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(self._fetch_single_ticker_info, ticker): ticker 
                for ticker in tickers
            }
            
            count = 0
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    info_data = future.result()
                    if info_data:
                        self._save_stock_info(ticker, info_data)
                    count += 1
                    if count % 10 == 0:
                        print(f"Synced {count}/{len(tickers)}...")
                except Exception as e:
                    print(f"Error syncing {ticker}: {e}")
                    
        print("Fundamental Sync Complete.")

    def _fetch_single_ticker_info(self, ticker: str):
        """
        Worker function: Fetch financials (Store DB) and Return Info dict.
        """
        # 1. Trigger the standard specific financial fetch (Income, BS, CF)
        # This writes directly to 'fundamentals' table via DataFetcher
        self.fund_fetcher.fetch_fundamentals(ticker)
        
        # 2. Fetch 'Info' for PEG, Sector, etc.
        try:
            t = yf.Ticker(ticker)
            # accessing .info triggers the request
            info = t.info 
            return info
        except:
            return None

    def _save_stock_info(self, ticker, info):
        """
        Saves snapshot data to stock_info table.
        """
        if not info:
            return

        record = (
            ticker,
            info.get('longName') or info.get('shortName'),
            info.get('sector'),
            info.get('industry'),
            info.get('marketCap'),
            info.get('pegRatio'),
            info.get('revenueGrowth'),
            info.get('returnOnEquity'),
            info.get('beta'),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        conn = self.store._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO stock_info 
            (ticker, company_name, sector, industry, market_cap, peg_ratio, 
             revenue_growth, return_on_equity, beta, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', record)
        conn.commit()
        conn.close()
