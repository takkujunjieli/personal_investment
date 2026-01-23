import sqlite3
import pandas as pd

def check_db(ticker):
    conn = sqlite3.connect('investment_data.db')
    cursor = conn.cursor()
    
    print(f"--- Checking DB for {ticker} ---")
    
    # Check count
    cursor.execute("SELECT count(*) FROM fundamentals WHERE ticker=?", (ticker,))
    count = cursor.fetchone()[0]
    print(f"Total records: {count}")
    
    if count == 0:
        print("[!] No records found!")
        conn.close()
        return

    # Check distinct metrics
    cursor.execute("SELECT DISTINCT metric FROM fundamentals WHERE ticker=?", (ticker,))
    metrics = [r[0] for r in cursor.fetchall()]
    print(f"Available Metrics ({len(metrics)}):")
    print(metrics[:10]) # Show first 10
    
    if "Net Income" in metrics:
        print("   [OK] 'Net Income' exists.")
    else:
        print("   [!] 'Net Income' NOT FOUND.")

    if "Total Stockholder Equity" in metrics:
        print("   [OK] 'Total Stockholder Equity' exists.")
    else:
        print("   [!] 'Total Stockholder Equity' NOT FOUND.")
        # Try to find similar
        print("   Similar to 'Equity':", [m for m in metrics if 'Equity' in m])

    # Check values for Net Income
    df = pd.read_sql_query("SELECT * FROM fundamentals WHERE ticker=? AND metric='Net Income'", conn, params=(ticker,))
    if not df.empty:
        print("Net Income Data:")
        print(df.head())
        
    conn.close()

if __name__ == "__main__":
    check_db("AAPL")
