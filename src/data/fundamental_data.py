import yfinance as yf
import pandas as pd
from src.data.store import DataStore
from datetime import datetime

class FundamentalDataFetcher:
    def __init__(self):
        self.store = DataStore()

    def fetch_fundamentals(self, ticker: str):
        """
        Fetches quarterly financials and stores them.
        """
        print(f"Fetching fundamentals for {ticker}...")
        stock = yf.Ticker(ticker)
        
        # We need a way to consolidate these into our long-format table
        # Table: ticker, report_date, metric, value
        
        dfs = []
        try:
            # Quarterly Balance Sheet
            qbs = stock.quarterly_balance_sheet
            if not qbs.empty:
                dfs.append(qbs)
            
            # Quarterly Financials (Income Statement)
            qfin = stock.quarterly_financials
            if not qfin.empty:
                dfs.append(qfin)
                
            # Quarterly Cashflow
            qcf = stock.quarterly_cashflow
            if not qcf.empty:
                dfs.append(qcf)
                
        except Exception as e:
            print(f"Error fetching fundamentals for {ticker}: {e}")
            return

        if not dfs:
            print("   [!] No fundamental data found.")
            return

        # Prepare records for DB
        records = []
        for df in dfs:
            # Standardize Index (trim spaces)
            df.index = df.index.astype(str).str.strip()
            
            # Columns are dates, Index are metrics
            for date_col in df.columns:
                try:
                    # yfinance dates can be timestamps or strings
                    if isinstance(date_col, pd.Timestamp):
                        date_str = date_col.strftime('%Y-%m-%d')
                    else:
                        date_str = str(date_col)
                        
                    for metric, value in df[date_col].items():
                        # Validate Value
                        if pd.isna(value):
                            continue
                            
                        val_float = 0.0
                        try:
                            val_float = float(value)
                        except:
                            continue
                            
                        records.append((ticker, date_str, str(metric), val_float))
                except Exception as e:
                    print(f"Error processing column {date_col}: {e}")
                    continue

        # Batch insert
        conn = self.store._get_conn()
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT OR REPLACE INTO fundamentals (ticker, report_date, metric, value)
            VALUES (?, ?, ?, ?)
        ''', records)
        conn.commit()
        conn.close()

    def get_metric_history(self, ticker: str, metric: str) -> pd.Series:
        """
        Returns a Series of a specific metric indexed by date.
        """
        conn = self.store._get_conn()
        query = "SELECT report_date, value FROM fundamentals WHERE ticker = ? AND metric = ? ORDER BY report_date ASC"
        df = pd.read_sql_query(query, conn, params=[ticker, metric], parse_dates=['report_date'])
        conn.close()
        
        if df.empty:
            return pd.Series()
        
        df.set_index('report_date', inplace=True)
        return df['value']

    def get_latest_metrics(self, ticker: str, metrics: list) -> dict:
        """
        Returns the latest available value for a list of metrics.
        """
        conn = self.store._get_conn()
        placeholders = ','.join(['?']*len(metrics))
        query = f'''
            SELECT metric, value, MAX(report_date) as date 
            FROM fundamentals 
            WHERE ticker = ? AND metric IN ({placeholders})
            GROUP BY metric
        '''
        
        params = [ticker] + metrics
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        data = {}
        for r in results:
            data[r[0]] = r[1]
        return data

    def get_live_info(self, ticker: str, keys: list) -> dict:
        """
        Fetches live data from yfinance info dict (e.g. PEG, Revenue Growth)
        Warning: Slower than DB lookup.
        """
        try:
            info = yf.Ticker(ticker).info
            return {k: info.get(k) for k in keys}
        except Exception as e:
            print(f"Error fetching info for {ticker}: {e}")
            return {k: None for k in keys}
