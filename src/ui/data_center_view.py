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

    # --- SECTION 2: DATA SYNCHRONIZATION ---
    st.header("2. Data Synchronization")
    combined_list = um.get_combined_universe()
    
    # Get Last Updated Date
    conn = store._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(last_updated) FROM stock_info")
    last_update_res = cursor.fetchone()
    last_updated_str = last_update_res[0] if last_update_res and last_update_res[0] else "Never"
    conn.close()
    
    st.info(f"Targeting **{len(combined_list)}** stocks (S&P500 + Nasdaq + Watchlist). Last Info Sync: **{last_updated_str}**")

    st.markdown("---")
    st.subheader("Step 1: Select Scope")
    
    # Scheduler Instance (Singleton) & Config
    from src.utils.scheduler import SyncScheduler
    scheduler = SyncScheduler()
    current_config = scheduler.load_config()
    
    # Discover available universes
    u_dir = Path("src/data/universes")
    available_univ = [f.stem for f in u_dir.glob("*.json")]
    
    # Default to config if available, else watchlist
    config_targets = current_config.get("targets", ["watchlist"])
    valid_defaults = [t for t in config_targets if t in available_univ]
    
    # 1. SHARED SELECTION
    selected_universes = st.multiselect(
        "Choose Universes to Sync:",
        options=available_univ,
        default=valid_defaults,
        help="This selection applies to both Manual and Auto-Sync."
    )
    
    st.subheader("Step 2: Choose Sync Method")
    sync_mode = st.radio("Mode:", ["Manual Trigger", "Auto-Schedule (Background)"], horizontal=True)
    
    if sync_mode == "Manual Trigger":
        st.markdown("**Manual Mode**: Run a batch update right now.")
        if st.button("🚀 Start Immediate Sync", type="primary"):
            if not selected_universes:
                st.warning("Please select at least one universe in Step 1.")
            else:
                # Execution Logic
                manual_combined = set()
                for t in selected_universes:
                    manual_combined.update(um.load_universe(t))
                
                target_list = sorted(list(manual_combined))
                
                if not target_list:
                    st.warning("Selected universes are empty.")
                else:
                    status_box = st.empty()
                    progress_bar = st.progress(0)
                    
                    st.info(f"Starting sync for **{len(target_list)}** tickers...")
                    
                    # 1. Price Sync
                    status_box.text("Phase 1: Batch Downloading Prices...")
                    updater.update_price_history(target_list)
                    progress_bar.progress(50)
                    
                    # 2. Fundamental Sync
                    status_box.text("Phase 2: Fetching Fundamentals & Info...")
                    chunk_size = 10
                    for i in range(0, len(target_list), chunk_size):
                        chunk = target_list[i : i+chunk_size]
                        updater.update_fundamentals_and_info(chunk, max_workers=5)
                        
                        pct = 50 + int((i / len(target_list)) * 50)
                        progress_bar.progress(min(pct, 99))
                        status_box.text(f"Phase 2: Processing {i}/{len(target_list)}...")
                        
                    progress_bar.progress(100)
                    status_box.success("✅ Sync Complete!")
                    time.sleep(1)
                    st.rerun()

    else: # Auto-Schedule
        st.markdown("**Auto Mode**: Configure background daily updates.")
        
        c1, c2 = st.columns(2)
        with c1:
            is_enabled = st.toggle("Enable Auto-Sync", value=current_config.get("enabled", False))
        with c2:
             # Time Schedule
            time_str = current_config.get("time", "06:00")
            try:
                default_time = datetime.strptime(time_str, "%H:%M").time()
            except:
                default_time = datetime.strptime("06:00", "%H:%M").time()
            scheduled_time = st.time_input("Daily Run Time", value=default_time)
            
        if st.button("💾 Save Auto-Sync Configuration"):
            new_config = {
                "enabled": is_enabled,
                "time": scheduled_time.strftime("%H:%M"),
                "targets": selected_universes # Saves the shared selection
            }
            scheduler._save_config(new_config)
            st.success("✅ Configuration & Scope Saved!")
            
            # Restart scheduler to apply changes
            if scheduler.running:
                scheduler.stop()
                scheduler.start()
            elif is_enabled:
                scheduler.start()
            
            time.sleep(0.5)
            st.rerun()
            
        # Status Monitor
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
