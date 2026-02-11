from src.data.store import DataStore
from src.data.batch_updater import BatchUpdater
import yfinance as yf
from datetime import datetime

def debug_aon():
    store = DataStore()
    last_date = store.get_latest_date("AON")
    print(f"AON Last Date: {last_date}")
    
    updater = BatchUpdater()
    print("Attempting to sync AON...")
    
    # Try the exact method
    try:
        updater.update_price_history(["AON"])
        print("Sync Success! (Check console for Timeout/Skip messages)")
    except Exception as e:
        print(f"Sync Failed: {e}")
        
    # Check sync_log
    try:
        conn = store._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sync_log WHERE ticker='AON'")
        row = cursor.fetchone()
        if row:
            print(f"Sync Log for AON: {row}")
        else:
            print("No entry in sync_log for AON (Means Success or Not Attempted)")
        conn.close()
    except Exception as e:
        print(f"Error checking log: {e}")

if __name__ == "__main__":
    debug_aon()
