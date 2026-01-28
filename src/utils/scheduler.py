import threading
import time
import json
import os
from datetime import datetime
from pathlib import Path
from src.data.batch_updater import BatchUpdater
from src.data.universe_manager import UniverseManager

CONFIG_PATH = Path("src/config/sync_config.json")

class SyncScheduler:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SyncScheduler, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.running = False
        self.thread = None
        self.status = "Stopped"
        self.last_run = "Never"
        self.next_run = "Not Scheduled"
        
        # Ensure config dir exists
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not CONFIG_PATH.exists():
            self._save_config({
                "enabled": False,
                "time": "06:00",
                "targets": ["watchlist"]
            })

    def _save_config(self, config):
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)

    def load_config(self):
        if not CONFIG_PATH.exists():
            return {"enabled": False, "time": "06:00", "targets": ["watchlist"]}
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except:
             return {"enabled": False, "time": "06:00", "targets": ["watchlist"]}

    def start(self):
        """Starts the background scheduler thread if not already running."""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.status = "Running"
        print("Scheduler started.")

    def stop(self):
        """Stops the background scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        self.status = "Stopped"
        print("Scheduler stopped.")

    def _run_loop(self):
        """Main loop checking time every minute."""
        while self.running:
            config = self.load_config()
            
            if not config.get("enabled", False):
                self.status = "Paused (Disabled in Config)"
                time.sleep(10)
                continue
                
            target_time = config.get("time", "06:00")
            now_str = datetime.now().strftime("%H:%M")
            
            self.status = f"Idle. Waiting for {target_time}..."
            
            if now_str == target_time:
                # Trigger Sync
                self._execute_sync(config.get("targets", []))
                # Sleep to avoid double trigger within same minute
                time.sleep(61)
            else:
                time.sleep(10)

    def _execute_sync(self, targets):
        self.status = "SYNCING..."
        print(f"Auto-Sync Triggered for: {targets}")
        
        try:
            um = UniverseManager()
            updater = BatchUpdater()
            
            combined_tickers = set()
            for target in targets:
                # 'target' matches filename stem from universe_manager
                # e.g. 'sp500', 'watchlist', 'nasdaq100'
                if target:
                    tickers = um.load_universe(target)
                    combined_tickers.update(tickers)
            
            ticker_list = sorted(list(combined_tickers))
            
            if not ticker_list:
                print("Auto-Sync: No tickers found to sync.")
                self.last_run = datetime.now().strftime("%Y-%m-%d %H:%M") + " (No Data)"
                return

            # Run Sync
            updater.update_price_history(ticker_list)
            
            # Chunking for fundamentals (simple loop here, no progress bar needed for background)
            chunk_size = 20
            for i in range(0, len(ticker_list), chunk_size):
                chunk = ticker_list[i : i+chunk_size]
                updater.update_fundamentals_and_info(chunk, max_workers=5)
            
            self.last_run = datetime.now().strftime("%Y-%m-%d %H:%M") + " (Success)"
            print("Auto-Sync Complete.")
            
        except Exception as e:
            print(f"Auto-Sync Failed: {e}")
            self.last_run = datetime.now().strftime("%Y-%m-%d %H:%M") + f" (Failed: {e})"
