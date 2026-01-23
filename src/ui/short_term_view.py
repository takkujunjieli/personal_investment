import streamlit as st
from src.engines.satellite_engine import SatelliteEngine

def render(tickers):
    st.title("Short-Term Strategy (The Sniper)")
    
    tab1, tab2 = st.tabs(["Event Driven (PEAD)", "Mean Reversion (VaR)"])
    
    engine = SatelliteEngine()

    with tab1:
        st.header("Post-Earnings Announcement Drift (PEAD)")
        st.markdown("Scans for stocks with **Gap Ups > 2%** and **Volume > 1.5x Avg** (Indicative of Earnings Surprise or Major News).")
        
        if st.button("Scan for PEAD"):
            with st.spinner("Scanning for gaps..."):
                df_pead = engine.scan_pead(tickers)
            
            if not df_pead.empty:
                st.success(f"Found {len(df_pead)} candidates!")
                st.dataframe(df_pead.style.format({
                    'gap_pct': '{:.2%}',
                    'current_return': '{:.2%}', 
                    'price': '${:.2f}'
                }))
            else:
                st.info("No PEAD candidates found today based on thresholds.")

    with tab2:
        st.header("Liquidity Crisis Alpha (VaR Breach)")
        st.markdown("""
        **Theory**: When VIX spikes, funds are forced to deleverage (Targeting Quality stocks).
        We look for **Quality Stocks** dropping more than their historical **VaR 95%** threshold.
        """)
        
        if st.button("Scan for Crisis Alpha"):
            with st.spinner("Checking VIX and Market Stress..."):
                df_rev = engine.scan_reversal(tickers)
            
            # Show VIX context
            vix, _ = engine.get_market_sentiment()
            if vix > 20:
                st.error(f"⚠️ High Volatility Alert: VIX = {vix:.2f}. Forced selling likely.")
            else:
                st.success(f"Market Calm: VIX = {vix:.2f}. Drops may be idiosyncratic.")

            if not df_rev.empty:
                st.dataframe(df_rev.style.format({
                    'drop': '{:.2%}',
                    'var_95': '{:.2%}',
                    'price': '${:.2f}'
                }))
            else:
                st.info("No VaR breaches found. Market is behaving within normal limits.")
