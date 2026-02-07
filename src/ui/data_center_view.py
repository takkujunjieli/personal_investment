import streamlit as st
import pandas as pd
from datetime import datetime
from src.data.universe_manager import UniverseManager
from src.data.batch_updater import BatchUpdater
from src.data.store import DataStore
from src.data.watchlist_manager import WatchlistManager
import time
from pathlib import Path

def render():
    st.title("📊 Dashboard & Data Center")
    
    # --- SECTION 0: SYSTEM OVERVIEW ---
    with st.expander("ℹ️ System Philosophy & Status", expanded=False):
        st.markdown("""
        ### Philosophy
        *   **Core**: Multi-Factor Investing (Quality + Value + Momentum).
        *   **Satellite**: Event-Driven (PEAD) & Reversal.
        *   **Architecture**: Database-First. Local SQLite for instant sub-second analysis.
        """)
    
    um = UniverseManager()
    updater = BatchUpdater()
    store = DataStore()
    
    # --- SECTION 1: UNIVERSE MANAGEMENT ---
    st.header("1. Universe Management")
    
    # helper for last mod time
    def get_file_date(filename):
        try:
            path = f"src/data/universes/{filename}"
            if os.path.exists(path):
                ts = os.path.getmtime(path)
                return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        except:
            pass
        return "Unknown"

    # Row 1: Standard Universes
    uc1, uc2 = st.columns(2)
    
    # S&P 500
    with uc1:
        # Header Row
        h1, h2 = st.columns([3, 1])
        with h1: 
            st.subheader("🇺🇸 S&P 500")
        with h2:
            if st.button("Update", key="btn_sp500", help="Scrape Wikipedia"):
                with st.spinner("Scraping..."):
                    try:
                        um.fetch_and_save_sp500()
                        st.success("Done!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"{e}")
        
        sp500_list = um.load_universe("sp500")
        st.caption(f"Count: **{len(sp500_list)}** | Last Updated: **{get_file_date('sp500.json')}**")

    # Nasdaq 100
    with uc2:
        # Header Row
        h1, h2 = st.columns([3, 1])
        with h1: 
            st.subheader("💻 Nasdaq 100")
        with h2:
            if st.button("Update", key="btn_ndx", help="Scrape Wikipedia"):
                with st.spinner("Scraping..."):
                    try:
                        um.fetch_and_save_nasdaq100()
                        st.success("Done!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"{e}")
        
        nasdaq_list = um.load_universe("nasdaq100")
        st.caption(f"Count: **{len(nasdaq_list)}** | Last Updated: **{get_file_date('nasdaq100.json')}**")

    st.markdown("") # Spacer

    # Row 2: Watchlist (Full Width -> Internal Columns)
    with st.container():
        st.subheader("👀 Watchlist Manager")
        watchlist = WatchlistManager.load_watchlist()
        st.caption(f"Current Watchlist Size: **{len(watchlist)}** tickers")
        
        wl_col1, wl_col2 = st.columns(2)
        
        # Add
        with wl_col1:
            c1, c2 = st.columns([3, 1]) 
            with c1:
                new_ticker = st.text_input("Add Ticker", placeholder="e.g. NVDA", label_visibility="collapsed").strip().upper()
            with c2:
                if st.button("Add", key="btn_add_wl"):
                    if new_ticker and new_ticker not in watchlist:
                        watchlist.append(new_ticker)
                        WatchlistManager.save_watchlist(watchlist)
                        st.success(f"+ {new_ticker}")
                        time.sleep(0.5)
                        st.rerun()
                    elif new_ticker in watchlist:
                        st.warning("Exists")

        # Remove
        with wl_col2:
            c1, c2 = st.columns([3, 1])
            with c1:
                to_remove = st.selectbox("Remove Ticker", ["Select..."] + watchlist, label_visibility="collapsed")
            with c2:
                if st.button("Remove", key="btn_rem_wl"):
                    if to_remove and to_remove in watchlist:
                        watchlist.remove(to_remove)
                        WatchlistManager.save_watchlist(watchlist)
                        st.success("Removed")
                        time.sleep(0.5)
                        st.rerun()

    st.divider()

    # --- SECTION 2: DATA STATUS ---
    st.header("2. Data Status")
    
    # Get Last Updated Date
    try:
        conn = store._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(last_updated) FROM stock_info")
        last_update_res = cursor.fetchone()
        last_updated_str = last_update_res[0] if last_update_res and last_update_res[0] else "Never"
        conn.close()
    except:
        last_updated_str = "Unknown"
    
    st.info(f"Last Info Sync: **{last_updated_str}**")
    
    # Check Scheduler
    from src.utils.scheduler import SyncScheduler
    scheduler = SyncScheduler()
    
    st.caption("---")
    st.caption("Service Status Monitor")
    
    col_a, col_b = st.columns(2)
    col_a.metric("Status", scheduler.status)
    col_b.metric("Last Run", scheduler.last_run)

    st.divider()
    
    # --- SECTION 3: DB STATUS ---
    st.subheader("Database Health")
    try:
        conn = store._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(DISTINCT ticker) FROM market_data")
        price_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT ticker) FROM stock_info")
        info_count = cursor.fetchone()[0]
        
        conn.close()
        
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Stocks with Price History", price_count)
        sc2.metric("Stocks with Fundamentals", info_count)
        sc3.metric("DB Path", "Local SQLite")
        
    except Exception as e:
        st.error(f"DB Error: {e}")
