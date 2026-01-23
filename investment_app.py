import streamlit as st
import pandas as pd
from src.utils import DEFAULT_TICKERS
from src.ui import long_term_view, short_term_view
from src.data.watchlist_manager import WatchlistManager

# Page Config
st.set_page_config(
    page_title="My Personal Quant",
    page_icon="🧠",
    layout="wide"
)

# Sidebar
st.sidebar.title("My Personal Quant")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", ["Dashboard", "Long-Term (Smart Beta)", "Short-Term (Sniper)", "Data Inspector", "Backtest Lab"])

# Global Ticker Selection - Session State Management
if 'watchlist' not in st.session_state:
    st.session_state['watchlist'] = WatchlistManager.load_watchlist()

st.sidebar.markdown("---")
st.sidebar.subheader("Watchlist Manager")

# Add Ticker
new_ticker = st.sidebar.text_input("Add Ticker").strip().upper()
if st.sidebar.button("Add"):
    if new_ticker and new_ticker not in st.session_state['watchlist']:
        st.session_state['watchlist'].append(new_ticker)
        WatchlistManager.save_watchlist(st.session_state['watchlist'])
        st.success(f"Added {new_ticker}")
    elif new_ticker in st.session_state['watchlist']:
        st.warning("Ticker already in watchlist")

# Watchlist Display & Selection
st.sidebar.markdown("### Current Watchlist")
watchlist = st.session_state['watchlist']

if not watchlist:
    st.sidebar.warning("Watchlist is empty!")

# Delete Ticker
to_remove = st.sidebar.selectbox("Select to Remove", [""] + watchlist)
if st.sidebar.button("Remove"):
    if to_remove in watchlist:
        watchlist.remove(to_remove)
        st.session_state['watchlist'] = watchlist
        WatchlistManager.save_watchlist(watchlist)
        st.rerun()

# Update Global Tickers for Analysis
tickers = watchlist
st.session_state['tickers'] = tickers

# Show Count
st.sidebar.caption(f"Total: {len(tickers)}")

# Routing
if page == "Dashboard":
    st.title("My Personal Quant")
    st.markdown("""
    ### Philosophy
    *   **Core**: Multi-Factor Investing (Quality + Value + Momentum).
    *   **Satellite**: Event-Driven (PEAD) & Reversal (VaR Breach).
    
    ### System Status
    *   **Data Source**: Yahoo Finance (Free Tier)
    *   **Storage**: Local SQLite (`investment_data.db`)
    *   **Universe Size**: {} stocks
    """.format(len(tickers)))
    
    st.info("Select a module from the sidebar to begin analysis.")

elif page == "Long-Term (Smart Beta)":
    long_term_view.render(tickers)

elif page == "Short-Term (Sniper)":
    short_term_view.render(tickers)

elif page == "Data Inspector":
    from src.ui import data_inspector_view
    data_inspector_view.render(tickers)

elif page == "Backtest Lab":
    from src.ui import backtest_view
    backtest_view.render(tickers)
