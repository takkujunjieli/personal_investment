import pandas as pd
import json
import os
import requests
from pathlib import Path

class UniverseManager:
    USA_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    NASDAQ_100_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    def __init__(self):
        self.base_dir = Path("src/data/universes")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def _fetch_html(self, url):
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise Exception(f"Network error fetching {url}: {str(e)}")

    def fetch_and_save_sp500(self):
        """
        Scrapes S&P 500 from Wikipedia and saves to sp500.json
        """
        print("Scraping S&P 500 list from Wikipedia...")
        try:
            html = self._fetch_html(self.USA_SP500_URL)
            tables = pd.read_html(html)
            if not tables:
                raise Exception("No tables found in Wikipedia page")
                
            df = tables[0]
            if 'Symbol' not in df.columns:
                raise Exception("Could not find 'Symbol' column in Table 0")
                
            # Ticker symbol in column 'Symbol'
            tickers = df['Symbol'].tolist()
            
            # Clean tickers (e.g., BRK.B -> BRK-B for yfinance)
            tickers = [str(t).replace('.', '-') for t in tickers]
            
            self._save_json("sp500", tickers)
            print(f"Saved {len(tickers)} tickers to sp500.json")
            return tickers
        except Exception as e:
            raise Exception(f"Failed to scrape S&P 500: {str(e)}")

    def fetch_and_save_nasdaq100(self):
        """
        Scrapes Nasdaq 100 from Wikipedia and saves to nasdaq100.json
        """
        print("Scraping Nasdaq 100 list from Wikipedia...")
        try:
            html = self._fetch_html(self.NASDAQ_100_URL)
            tables = pd.read_html(html)
            
            # The table with constituents is usually relevant
            df = None
            for table in tables:
                if 'Ticker' in table.columns:
                    df = table
                    break
                elif 'Symbol' in table.columns:
                    df = table
                    break
            
            if df is None:
                raise Exception("Could not find table with Ticker/Symbol on Nasdaq page")

            col_name = 'Ticker' if 'Ticker' in df.columns else 'Symbol'
            tickers = df[col_name].tolist()
            
            # Clean tickers
            tickers = [str(t).replace('.', '-') for t in tickers]
            
            self._save_json("nasdaq100", tickers)
            print(f"Saved {len(tickers)} tickers to nasdaq100.json")
            return tickers
        except Exception as e:
            raise Exception(f"Failed to scrape Nasdaq 100: {str(e)}")

    def _save_json(self, name, tickers):
        path = self.base_dir / f"{name}.json"
        with open(path, 'w') as f:
            json.dump(tickers, f, indent=4)
            
    def load_universe(self, name):
        path = self.base_dir / f"{name}.json"
        if not path.exists():
            return []
        with open(path, 'r') as f:
            return json.load(f)
            
    def get_combined_universe(self, include_watchlist=True):
        """
        Returns unique tickers from all system universes + user watchlist.
        """
        tickers = set()
        
        # System Universes
        for name in ['sp500', 'nasdaq100']:
            u = self.load_universe(name)
            tickers.update(u)
            
        # User Watchlist
        if include_watchlist:
            try:
                # Naive load relative to CWD
                if os.path.exists("watchlist.json"):
                    with open("watchlist.json", "r") as f:
                        user_list = json.load(f)
                        tickers.update(user_list)
            except:
                pass
                
        return sorted(list(tickers))
