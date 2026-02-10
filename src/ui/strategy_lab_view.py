import streamlit as st
import pandas as pd
from src.engines.stock_selection_engine import StockSelectionEngine
from src.engines.strategy_registry import (
    SmaCrossStrategy, RsiMeanReversionStrategy, 
    PeadStrategy, LiquidityCrisisStrategy
)

def render(tickers):
    st.title("🧪 Strategy Lab")
    st.caption("Design your Stock Selection criteria and calibrate Market Timing strategies.")
    
    tab_select, tab_time = st.tabs(["📊 Stock Selection (选股)", "⏱️ Market Timing (择时)"])
    
    # ---------------------------------------------------------
    # TAB 1: STOCK SELECTION (选股)
    # ---------------------------------------------------------
    with tab_select:
        col_method, col_action = st.columns([2, 1])
        with col_method:
            selection_method = st.selectbox(
                "Selection Method",
                [
                    "High Quality (Composite Score)", 
                    "Undervalued (Magic Formula)", 
                    "Growth (GARP)"
                ],
                help="Choose the fundamental framework for ranking stocks."
            )
            
        with col_action:
            st.write("") # Spacer
            st.write("")
            run_btn = st.button("Run Screener", type="primary")
            
        # ---------------------------------------------------------
        # State Management & Execution
        # ---------------------------------------------------------
        if run_btn:
            engine = StockSelectionEngine()
            with st.spinner(f"Ranking stocks using {selection_method}..."):
                df = pd.DataFrame()
                current_cols = []
                
                if "High Quality" in selection_method:
                    df = engine.rank_stocks(tickers)
                    current_cols = ['ticker', 'composite_score', 'momentum_12m', 'roe', 'z_score', 'close']
                elif "Undervalued" in selection_method:
                    df = engine.rank_magic_formula(tickers)
                    current_cols = ['ticker', 'magic_score', 'roc', 'earnings_yield', 'close']
                elif "Growth" in selection_method:
                    df = engine.rank_garp(tickers)
                    current_cols = ['ticker', 'garp_score', 'peg', 'growth', 'roe', 'close']
            
            if not df.empty:
                # Save to Session State
                st.session_state['screener_result'] = df
                st.session_state['screener_cols'] = current_cols
                # Force a rerun to show results immediately from state (optional, but cleaner flow) or just fall through
            else:
                st.warning("No data returned. Try Syncing Data first.")
                # Clear previous results if run fails? Or keep them? 
                # Let's keep them but show warning ensures user knows this run failed.
        
        # ---------------------------------------------------------
        # Display Logic (from Session State)
        # ---------------------------------------------------------
        if 'screener_result' in st.session_state:
            df = st.session_state['screener_result']
            display_cols = st.session_state['screener_cols']
            
            st.divider()
            
            # Setup Session State for Lab
            if 'backtest_tickers' not in st.session_state:
                st.session_state['backtest_tickers'] = []
            
            # Re-evaluate "Add to Lab" every render to match current backtest_tickers state
            # (In case user removed them in another tab)
            df['Add to Lab'] = df['ticker'].isin(st.session_state['backtest_tickers'])
            
            final_cols = ['Add to Lab'] + display_cols
            
            # Checkbox Editor
            edited_df = st.data_editor(
                df[final_cols].head(50).style.format(precision=2), # Increased to 50
                column_config={
                    "Add to Lab": st.column_config.CheckboxColumn("Add to Lab", default=False),
                    "ticker": st.column_config.TextColumn("Ticker", disabled=True),
                },
                disabled=display_cols,
                hide_index=True,
                use_container_width=True,
                key="screener_editor"
            )
            
            # Sync Logic
            if edited_df is not None:
                selected = edited_df[edited_df['Add to Lab'] == True]['ticker'].tolist()
                current = st.session_state['backtest_tickers']
                
                # We need to be careful not to delete tickers that are NOT in the screener list
                # but ARE in the backtest list (added from elsewhere).
                
                # 1. Identify tickers visible in this screener result
                visible_tickers = df['ticker'].tolist()
                
                # 2. Add newly selected
                for t in selected:
                    if t not in current:
                        current.append(t)
                
                # 3. Remove deselected (ONLY if they are in the visible set)
                for t in visible_tickers:
                    if t not in selected and t in current:
                        current.remove(t)
                
                st.session_state['backtest_tickers'] = current
                
                # Show summary
                st.caption(f"Active Backtest Universe: {len(current)} tickers")


    # ---------------------------------------------------------
    # TAB 2: MARKET TIMING (择时)
    # ---------------------------------------------------------
    # ---------------------------------------------------------
    # TAB 2: MARKET TIMING (择时)
    # ---------------------------------------------------------
    with tab_time:
        st.subheader("Strategy Configuration & Scanner")
        st.info("Configure parameters here. Scans run on live data, Backtests run on historical data.")
        
        # Initialize Strategy Registry
        strategies = [
            SmaCrossStrategy(),
            RsiMeanReversionStrategy(),
            PeadStrategy(),
            LiquidityCrisisStrategy()
        ]
        
        # Load existing params from session or init
        if 'strategy_params' not in st.session_state:
            st.session_state['strategy_params'] = {}
            
        stored_params = st.session_state['strategy_params']
        
        # Render Config Widgets
        cols_cfg = st.columns(2)
        for i, strat in enumerate(strategies):
            with cols_cfg[i % 2]:
                with st.expander(f"⚙️ {strat.name}", expanded=False):
                    defaults = strat.default_params
                    current_vals = stored_params.get(strat.name, defaults.copy())
                    new_vals = {}
                    
                    for key, val in defaults.items():
                        widget_key = f"conf_{strat.name}_{key}"
                        if isinstance(val, int):
                            new_vals[key] = st.number_input(key, value=current_vals.get(key, val), step=1, key=widget_key)
                        elif isinstance(val, float):
                            new_vals[key] = st.number_input(key, value=current_vals.get(key, val), step=0.01, format="%.2f", key=widget_key)
                        else:
                            new_vals[key] = val
                    
                    stored_params[strat.name] = new_vals
                    
        st.session_state['strategy_params'] = stored_params
        
        st.divider()
        
        # Scanner Section
        st.subheader("📡 Live Scanner")
        
        col_scan1, col_scan2 = st.columns(2)
        
        # Scanner 1: PEAD
        with col_scan1:
            st.markdown("#### Event Driven (PEAD)")
            st.caption("Scans for stocks with Gap Ups > Threshold")
            
            if st.button("Scan for PEAD Candidates"):
                # Get params
                pead_params = stored_params.get("Event Driven (PEAD)", {})
                
                from src.engines.market_timing_engine import MarketTimingEngine
                timing_engine = MarketTimingEngine()
                
                with st.spinner("Scanning Intraday Data..."):
                    df_pead = timing_engine.scan_pead(tickers, **pead_params)
                
                if not df_pead.empty:
                    st.success(f"Found {len(df_pead)} candidates!")
                    st.dataframe(df_pead.style.format({
                        'gap_pct': '{:.2%}',
                        'current_return': '{:.2%}', 
                        'price': '${:.2f}'
                    }))
                else:
                    st.info("No PEAD candidates found today.")

        # Scanner 2: Liquidity Crisis
        with col_scan2:
            st.markdown("#### Mean Reversion (VaR)")
            st.caption("Scans for VaR Breaches + High VIX")
            
            if st.button("Scan for Crisis Alpha"):
                # Get params
                var_params = stored_params.get("Mean Reversion (VaR)", {})
                
                from src.engines.market_timing_engine import MarketTimingEngine
                timing_engine = MarketTimingEngine()
                
                with st.spinner("Checking VIX and Market Stress..."):
                    df_rev = timing_engine.scan_reversal(tickers, **var_params)
                
                # Show VIX context
                vix, _ = timing_engine.get_market_sentiment()
                if vix > 20:
                    st.error(f"⚠️ High Volatility Alert: VIX = {vix:.2f}")
                else:
                    st.success(f"Market Calm: VIX = {vix:.2f}")

                if not df_rev.empty:
                    st.dataframe(df_rev.style.format({
                        'drop': '{:.2%}',
                        'var_95': '{:.2%}',
                        'price': '${:.2f}'
                    }))
                else:
                    st.info("No VaR breaches found.")

