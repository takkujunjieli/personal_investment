import streamlit as st
import pandas as pd
from src.engines.core_engine import CoreEngine
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
            
        if run_btn:
            engine = CoreEngine()
            with st.spinner(f"Ranking stocks using {selection_method}..."):
                if "High Quality" in selection_method:
                    df = engine.rank_stocks(tickers)
                    display_cols = ['ticker', 'composite_score', 'momentum_12m', 'roe', 'z_score', 'close']
                elif "Undervalued" in selection_method:
                    df = engine.rank_magic_formula(tickers)
                    display_cols = ['ticker', 'magic_score', 'roc', 'earnings_yield', 'close']
                elif "Growth" in selection_method:
                    df = engine.rank_garp(tickers)
                    display_cols = ['ticker', 'garp_score', 'peg', 'growth', 'roe', 'close']
            
            if not df.empty:
                # Add "Add to Backtest Lab" logic here too?
                # For now, just show the table. Usage flow: Synced -> View Here -> Add to Lab?
                # User asked to "Add to Lab" check in previous task. 
                # Ideally we replicate the "Add to Lab" editor here.
                
                # Setup Session State for Lab
                if 'backtest_tickers' not in st.session_state:
                    st.session_state['backtest_tickers'] = []
                
                df['Add to Lab'] = df['ticker'].isin(st.session_state['backtest_tickers'])
                
                final_cols = ['Add to Lab'] + display_cols
                
                # Checkbox Editor
                edited_df = st.data_editor(
                    df[final_cols].head(20).style.format(precision=2),
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
                    # Add new selected
                    for t in selected:
                        if t not in current:
                            current.append(t)
                    # Remove unselected (only from those visible in list to avoid clearing hidden ones)
                    visible = edited_df['ticker'].tolist()
                    for t in visible:
                        if t not in selected and t in current:
                            current.remove(t)
                    
                    st.session_state['backtest_tickers'] = current
                    st.success(f"Backtest Lab List Updated: {len(current)} tickers")

            else:
                st.warning("No data returned. Try Syncing Data first.")

    # ---------------------------------------------------------
    # TAB 2: MARKET TIMING (择时)
    # ---------------------------------------------------------
    with tab_time:
        st.subheader("Strategy Configuration")
        st.info("Configure parameters here. These settings will be applied in the Backtest Lab.")
        
        # Initialize Strategy Registry
        # We define them here to get access to default_params
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
        cols = st.columns(2)
        for i, strat in enumerate(strategies):
            with cols[i % 2]:
                with st.expander(f"⚙️ {strat.name}", expanded=True):
                    # Get defaults
                    defaults = strat.default_params
                    # Get Value from session or default
                    current_vals = stored_params.get(strat.name, defaults.copy())
                    
                    # Store updated values temporarily
                    new_vals = {}
                    
                    for key, val in defaults.items():
                        # Create a unique key for streamlit widget
                        widget_key = f"conf_{strat.name}_{key}"
                        
                        if isinstance(val, int):
                            new_vals[key] = st.number_input(
                                key, 
                                value=current_vals.get(key, val), 
                                step=1,
                                key=widget_key
                            )
                        elif isinstance(val, float):
                            new_vals[key] = st.number_input(
                                key, 
                                value=current_vals.get(key, val), 
                                step=0.01, 
                                format="%.2f",
                                key=widget_key
                            )
                        else:
                            new_vals[key] = val
                    
                    # Update Session State immediately on change
                    stored_params[strat.name] = new_vals
                    
        # Save back to global state (redundant but safe)
        st.session_state['strategy_params'] = stored_params

