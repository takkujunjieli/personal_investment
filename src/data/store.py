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
        
        # Ranking History Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ranking_history (
                strategy TEXT,
                date TEXT,
                ticker TEXT,
                rank INTEGER,
                score REAL,
                PRIMARY KEY (strategy, date, ticker)
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

    def get_latest_dates(self, tickers: list) -> dict:
        """
        Returns {ticker: latest_date_str} for a list of tickers.
        """
        if not tickers:
            return {}
            
        conn = self._get_conn()
        placeholders = ','.join(['?'] * len(tickers))
        query = f'''
            SELECT ticker, MAX(date) 
            FROM market_data 
            WHERE ticker IN ({placeholders}) 
            GROUP BY ticker
        '''
        
        try:
            cursor = conn.cursor()
            cursor.execute(query, tickers)
            results = cursor.fetchall() # [(ticker, date), ...]
            return {row[0]: row[1] for row in results}
        except Exception as e:
            print(f"Error batch fetching dates: {e}")
            return {}
        finally:
            conn.close()

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

    def save_ranking_history(self, strategy: str, df: pd.DataFrame):
        """
        Saves the ranking results to the history table.
        """
        if df.empty:
            return

        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Ensure table exists (in case it wasn't created in init)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ranking_history (
                strategy TEXT,
                date TEXT,
                ticker TEXT,
                rank INTEGER,
                score REAL,
                PRIMARY KEY (strategy, date, ticker)
            )
        ''')
        
        today = pd.Timestamp.now().strftime('%Y-%m-%d')
        
        records = []
        for rank, row in df.iterrows():
            score = row.get('composite_score') if 'composite_score' in row else row.get('magic_score', 0)
            
            records.append((
                strategy,
                today,
                row['ticker'],
                rank + 1,
                score
            ))
            
        try:
            cursor.executemany('''
                INSERT OR REPLACE INTO ranking_history (strategy, date, ticker, rank, score)
                VALUES (?, ?, ?, ?, ?)
            ''', records)
            conn.commit()
        except Exception as e:
            print(f"Error saving ranking history: {e}")
        finally:
            conn.close()

    def save_sync_status(self, tickers: list, status: str):
        """
        Logs sync status (e.g. TIMEOUT) for tickers.
        """
        if not tickers:
            return
            
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_log (
                ticker TEXT PRIMARY KEY,
                status TEXT,
                last_attempt TEXT
            )
        ''')
        
        now = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        records = [(t, status, now) for t in tickers]
        
        cursor.executemany('''
            INSERT OR REPLACE INTO sync_log (ticker, status, last_attempt)
            VALUES (?, ?, ?)
        ''', records)
        
        conn.commit()
        conn.close()

    def get_previous_rankings(self, strategy: str) -> dict:
        """
        Returns {ticker: rank} for the most recent run BEFORE today.
        """
        conn = self._get_conn()
        today = pd.Timestamp.now().strftime('%Y-%m-%d')
        
        # Find latest date that is NOT today
        cursor = conn.cursor()
        cursor.execute('''
            SELECT MAX(date) FROM ranking_history 
            WHERE strategy = ? AND date < ?
        ''', (strategy, today))
        
        result = cursor.fetchone()
        last_date = result[0] if result else None
        
        if not last_date:
            conn.close()
            return {}
            
        # Fetch rankings for that date
        df = pd.read_sql_query('''
            SELECT ticker, rank FROM ranking_history
            WHERE strategy = ? AND date = ?
        ''', conn, params=(strategy, last_date))
        
        conn.close()
        
        if df.empty:
            return {}
            
        return df.set_index('ticker')['rank'].to_dict()
