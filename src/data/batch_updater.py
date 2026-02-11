import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from src.data.store import DataStore
from src.data.fundamental_data import FundamentalDataFetcher

class BatchUpdater:
    def __init__(self):
        self.store = DataStore()
        self.fund_fetcher = FundamentalDataFetcher()

    def update_price_history(self, tickers: list):
        """
        Batch downloads price history incrementally.
        Uses ThreadPoolExecutor with timeout to skip stalled tickers.
        """
        print(f"Batch Syncing Prices for {len(tickers)} tickers...")
        
        # 1. Check existing dates
        try:
            latest_dates = self.store.get_latest_dates(tickers) # {ticker: 'YYYY-MM-DD'}
        except:
            latest_dates = {}
            
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        # 2. Group tickers by start date
        groups = {'NEW': []}
        
        for t in tickers:
            ld = latest_dates.get(t)
            if not ld:
                groups['NEW'].append(t)
            else:
                if ld not in groups:
                    groups[ld] = []
                groups[ld].append(t)
        
        # 3. Flatten the list of tasks [(ticker, start_date, period)]
        tasks = []
        
        # New tickers
        for t in groups['NEW']:
            tasks.append({'ticker': t, 'period': '2y', 'start': None})
            
        # Incremental tickers
        for last_date, batch in groups.items():
            if last_date == 'NEW': continue
            
            start_dt = datetime.strptime(last_date, '%Y-%m-%d') + timedelta(days=1)
            if start_dt > datetime.now():
                continue # Up to date
                
            start_str = start_dt.strftime('%Y-%m-%d')
            for t in batch:
                tasks.append({'ticker': t, 'start': start_str, 'period': None})
                
        print(f"Total separate download tasks: {len(tasks)}")
        
        # 4. Execute with Timeout
        skipped_tickers = []
        success_count = 0
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Map future to task info
            future_to_task = {
                executor.submit(self._fetch_single, task): task['ticker']
                for task in tasks
            }
            
            for future in as_completed(future_to_task):
                ticker = future_to_task[future]
                try:
                    # 5 Second Timeout
                    data = future.result(timeout=5)
                    if data is not None and not data.empty:
                        self.store.save_market_data(ticker, data)
                        success_count += 1
                except TimeoutError:
                    print(f"TIMEOUT: Skipping {ticker} (took > 5s)")
                    skipped_tickers.append(ticker)
                except Exception as e:
                    print(f"Error fetching {ticker}: {e}")
                    skipped_tickers.append(ticker)
                    
        print(f"Sync Complete. Success: {success_count}, Skipped/Failed: {len(skipped_tickers)}")
        
        # Save skipped tickers to DB for visibility
        if skipped_tickers:
            self.store.save_sync_status(skipped_tickers, status="TIMEOUT")

    def _fetch_single(self, task):
        """
        Helper for single ticker download.
        """
        ticker = task['ticker']
        period = task.get('period')
        start = task.get('start')
        
        # Use yf.download for single ticker
        try:
            df = yf.download(ticker, period=period, start=start, progress=False, threads=False)
            if not df.empty:
                # Cleanup
                if isinstance(df.columns, pd.MultiIndex):
                     df.columns = df.columns.droplevel(1)
                df = df.dropna(how='all')
                return df
        except Exception:
            pass
        return None

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
