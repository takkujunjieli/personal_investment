import sqlite3
import pandas as pd
from pathlib import Path
import threading

class DataStore:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path="investment_data.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DataStore, cls).__new__(cls)
                    cls._instance._init_db(db_path)
        return cls._instance

    def _init_db(self, db_path):
        self.db_path = db_path
        self._create_tables()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Market Data Table (Daily OHLCV)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                ticker TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                PRIMARY KEY (ticker, date)
            )
        ''')
        
        # Fundamentals Table (Quarterly)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fundamentals (
                ticker TEXT,
                report_date TEXT,
                metric TEXT,
                value REAL,
                PRIMARY KEY (ticker, report_date, metric)
            )
        ''')

        # Stock Info Snapshot Table (Reference Data)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_info (
                ticker TEXT PRIMARY KEY,
                company_name TEXT,
                sector TEXT,
                industry TEXT,
                market_cap REAL,
                peg_ratio REAL,
                revenue_growth REAL,
                return_on_equity REAL,
                beta REAL,
                last_updated TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def save_market_data(self, ticker: str, df: pd.DataFrame):
        """
        Saves DataFrame with DateTime index and OHLCV columns to DB.
        """
        if df.empty:
            return
        
        # Ensure index is datetime and columns exist
        df = df.copy()
        df.reset_index(inplace=True)
        # Standardize column names
        df.columns = [c.lower() for c in df.columns]
        
        # Rename 'Date' column if needed (yfinance usually returns 'Date')
        if 'date' not in df.columns:
             # Try to find a date-like column
             pass 

        records = []
        for _, row in df.iterrows():
            # Format date as YYYY-MM-DD
            date_str = row['date'].strftime('%Y-%m-%d')
            records.append((
                ticker, 
                date_str, 
                row.get('open', 0), 
                row.get('high', 0), 
                row.get('low', 0), 
                row.get('close', 0), 
                int(row.get('volume', 0))
            ))

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT OR REPLACE INTO market_data (ticker, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', records)
        conn.commit()
        conn.close()

    def get_market_data(self, ticker: str, start_date: str = None) -> pd.DataFrame:
        conn = self._get_conn()
        query = "SELECT date, open, high, low, close, volume FROM market_data WHERE ticker = ?"
        params = [ticker]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
            
        query += " ORDER BY date ASC"
        
        df = pd.read_sql_query(query, conn, params=params, parse_dates=['date'])
        conn.close()
        
        if not df.empty:
            df.set_index('date', inplace=True)
            
        return df

    def get_latest_date(self, ticker: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(date) FROM market_data WHERE ticker = ?", (ticker,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def get_latest_stock_info(self, tickers: list) -> dict:
        """
        Returns a dict of {ticker: {info_dict}} for a list of tickers.
        Efficient batch query.
        """
        if not tickers:
            return {}

        conn = self._get_conn()
        # Create placeholders for IN clause
        placeholders = ','.join(['?'] * len(tickers))
        query = f"SELECT * FROM stock_info WHERE ticker IN ({placeholders})"
        
        try:
            df = pd.read_sql_query(query, conn, params=tickers)
        except Exception as e:
            print(f"Error fetching stock info: {e}")
            conn.close()
            return {}
            
        conn.close()
        
        if df.empty:
            return {}
            
        # Convert to dictionary formatted like {ticker: {...}}
        # 'records' orientation gives [{col: val, ...}, ...]
        # We want to index by ticker
        df.set_index('ticker', inplace=True)
        return df.to_dict(orient='index')

    def get_latest_fundamentals(self, tickers: list, metrics: list) -> dict:
        """
        Returns {ticker: {metric: value}} for the latest available date for each metric.
        """
        if not tickers or not metrics:
            return {}

        conn = self._get_conn()
        ticker_holders = ','.join(['?'] * len(tickers))
        metric_holders = ','.join(['?'] * len(metrics))
        
        # Complex query to get the latest value for each (ticker, metric) pair
        # We group by ticker and metric and find the max report_date
        query = f'''
            SELECT f.ticker, f.metric, f.value
            FROM fundamentals f
            INNER JOIN (
                SELECT ticker, metric, MAX(report_date) as max_date
                FROM fundamentals
                WHERE ticker IN ({ticker_holders})
                  AND metric IN ({metric_holders})
                GROUP BY ticker, metric
            ) latest 
            ON f.ticker = latest.ticker 
           AND f.metric = latest.metric 
           AND f.report_date = latest.max_date
        '''
        
        params = tickers + metrics
        try:
            df = pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            print(f"Error fetching batch fundamentals: {e}")
            conn.close()
            return {}
            
        conn.close()
        
        if df.empty:
            return {}
            
        # Pivot to {ticker: {metric: value}}
        # Pivot table: Index=ticker, Columns=metric, Values=value
        pivot = df.pivot(index='ticker', columns='metric', values='value')
        return pivot.to_dict(orient='index')
