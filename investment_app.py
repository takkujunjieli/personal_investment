import streamlit as st
import pandas as pd
from src.utils import DEFAULT_TICKERS
from src.ui import long_term_view, short_term_view
from src.data.watchlist_manager import WatchlistManager
from src.data.universe_manager import UniverseManager
from pathlib import Path

# Page Config
st.set_page_config(
    page_title="My Personal Quant",
    page_icon="🧠",
    layout="wide"
)

# --- BACKGROUND SERVICES ---
from src.utils.scheduler import SyncScheduler

@st.cache_resource
def start_scheduler():
    scheduler = SyncScheduler()
    # It will verify config and start if enabled
    scheduler.start()
    return scheduler

# Initialize Background Scheduler (Singleton)
_ = start_scheduler()

# Sidebar
st.sidebar.title("My Personal Quant")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", ["Dashboard", "Strategy Lab", "Backtest Lab"])

# --- ANALYSIS SCOPE ---
st.sidebar.markdown("---")
st.sidebar.subheader("Analysis Scope")

# 1. Discover Universe Files
universe_dir = Path("src/data/universes")
universe_files = [f.stem for f in universe_dir.glob("*.json")]
if "watchlist" in universe_files:
    # Ensure watchlist is top option
    universe_files.remove("watchlist")
    universe_files.insert(0, "watchlist")

# 2. Multi-Select Universe
selected_universes = st.sidebar.multiselect(
    "Select Universe(s):", 
    options=universe_files, 
    default=["watchlist"] if "watchlist" in universe_files else None
)

# 3. Load & Merge Tickers
active_tickers = set()
um = UniverseManager() # Helper for consistency

if not selected_universes:
    st.sidebar.warning("Select at least one universe.")
    tickers = []
else:
    for univ_name in selected_universes:
        try:
            u_list = um.load_universe(univ_name)
            active_tickers.update(u_list)
        except Exception as e:
            st.sidebar.error(f"Error loading {univ_name}: {e}")
    
    # Convert to sorted list
    full_list = sorted(list(active_tickers))
    
    # 4. Filter / Refinement
    with st.sidebar.expander(f"Refine Selection ({len(full_list)})", expanded=False):
        tickers = st.multiselect(
            "Filter Active Tickers:", 
            full_list, 
            default=full_list
        )
        
    if not tickers:
        tickers = []

st.sidebar.caption(f"Active Analysis Set: {len(tickers)} stocks")

# --- TRADE SIZER (Risk Management) ---
st.sidebar.divider()
with st.sidebar.expander("🧮 Trade Sizer", expanded=False):
    st.caption("Position Sizing Calculator")
    
    # Account Inputs
    account_size = st.number_input("Account ($)", value=100000, step=5000)
    risk_pct = st.number_input("Risk per Trade (%)", value=1.0, step=0.5, format="%.1f") / 100.0
    
    # Trade Inputs
    entry_price = st.number_input("Entry Price", value=100.0, step=1.0)
    stop_loss = st.number_input("Stop Loss", value=90.0, step=1.0)
    target_price = st.number_input("Target Price", value=130.0, step=1.0)
    
    if entry_price > 0 and stop_loss > 0:
        # Calculate Risk
        risk_per_share = abs(entry_price - stop_loss)
        reward_per_share = abs(target_price - entry_price)
        
        if risk_per_share == 0:
            st.error("Stop Loss cannot equal Entry!")
        else:
            # 1. R/R Ratio
            rr_ratio = reward_per_share / risk_per_share
            
            # 2. Position Size
            max_risk_dollar = account_size * risk_pct
            position_shares = int(max_risk_dollar / risk_per_share)
            position_value = position_shares * entry_price
            
            # Display
            st.markdown("---")
            
            # R/R Color Coding
            rr_color = "red"
            if rr_ratio >= 3.0: rr_color = "green"
            elif rr_ratio >= 1.5: rr_color = "orange"
            
            st.markdown(f"**R/R Ratio**: :{rr_color}[{rr_ratio:.2f}]")
            
            col1, col2 = st.columns(2)
            col1.metric("Shares", f"{position_shares}")
            col2.metric("Risk ($)", f"${max_risk_dollar:.0f}")
            
            st.caption(f"Total Exposure: ${position_value:,.0f}")
            
            # Warnings
            if rr_ratio < 1.5:
                st.warning("Skipping recommended (Low R/R)")
            if position_value > account_size:
                st.error("⚠️ Leverage Required!")

# Routing
# Routing
if page == "Dashboard":
    from src.ui import data_center_view
    data_center_view.render()

elif page == "Strategy Lab":
    from src.ui import strategy_lab_view
    strategy_lab_view.render(tickers)

elif page == "Backtest Lab":
    from src.ui import backtest_view
    backtest_view.render(tickers)
