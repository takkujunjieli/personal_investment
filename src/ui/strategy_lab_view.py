import streamlit as st
from src.ui import long_term_view, short_term_view

def render(tickers):
    st.title("🧪 Strategy Lab")
    
    tab1, tab2 = st.tabs(["🔭 Long-Term Strategy", "🎯 Short-Term (Sniper)"])
    
    with tab1:
        long_term_view.render(tickers)
        
    with tab2:
        short_term_view.render(tickers)
