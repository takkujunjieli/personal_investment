import json
import os

WATCHLIST_FILE = "src/data/universes/watchlist.json"

class WatchlistManager:
    @staticmethod
    def load_watchlist() -> list:
        """
        Loads tickers from JSON file. Returns default list if file missing.
        """
        if not os.path.exists(WATCHLIST_FILE):
            # Default starter pack
            return ["AAPL", "MSFT", "GOOG", "NVDA", "SPY", "^VIX"] 
        
        try:
            with open(WATCHLIST_FILE, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [str(t).upper() for t in data]
                return []
        except Exception as e:
            print(f"Error loading watchlist: {e}")
            return []

    @staticmethod
    def save_watchlist(tickers: list):
        """
        Saves current list of tickers to JSON file.
        """
        try:
            # Deduplicate and sort
            unique_tickers = sorted(list(set(tickers)))
            with open(WATCHLIST_FILE, 'w') as f:
                json.dump(unique_tickers, f, indent=4)
        except Exception as e:
            print(f"Error saving watchlist: {e}")
