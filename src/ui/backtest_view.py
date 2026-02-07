import streamlit as st
import pandas as pd
import plotly.express as px
from src.data.market_data import MarketDataFetcher
from src.engines.backtest_engine import BacktestEngine
from src.engines.strategy_registry import SmaCrossStrategy, RsiMeanReversionStrategy

def render(tickers):
    st.header("Backtest Lab 🧪")
    
    # 1. Asset Selection
    col1, col2 = st.columns([1, 1])
    with col1:
        # Default from session state if available
        default_tickers = st.session_state.get('backtest_tickers', [])
        # Ensure defaults are in options
        current_options = sorted(list(set(tickers + default_tickers)))
        
        # Multi-select
        selected_assets = st.multiselect("Select Asset(s)", current_options, default=default_tickers, key="bt_ticker")
        
        # Update session state on change
        st.session_state['backtest_tickers'] = selected_assets
        
    # 2. Strategy Selection
    with col2:
        strategies = {
            "SMA Trend Following": SmaCrossStrategy(),
            "RSI Mean Reversion": RsiMeanReversionStrategy()
        }
        strategy_name = st.selectbox("Select Strategy", list(strategies.keys()))
        selected_strategy = strategies[strategy_name]
    
    fetcher = MarketDataFetcher()
    
    # 3. Strategy Configuration (Dynamic)
    st.subheader("Strategy Parameters")
    params = selected_strategy.default_params.copy()
    
    # Simple dynamic form generation based on default params
    cols = st.columns(len(params))
    for i, (key, default_val) in enumerate(params.items()):
        with cols[i]:
            if isinstance(default_val, int):
                params[key] = st.number_input(key, value=default_val, step=1)
            elif isinstance(default_val, float):
                params[key] = st.number_input(key, value=default_val, step=0.1)
                
    st.markdown("---")

    if st.button("🚀 Run Portfolio Backtest", type="primary"):
        if not selected_assets:
            st.warning("Please select at least one asset.")
            return

        with st.spinner(f"Simulating Strategy on {len(selected_assets)} assets..."):
            # 1. Fetch Data for all assets
            market_data = {}
            # Check for Analysis Span
            period = st.session_state.get('analysis_span', '1y')
            
            progress = st.progress(0)
            for i, t in enumerate(selected_assets):
                df = fetcher.fetch_data(t, period=period)
                if not df.empty:
                    market_data[t] = df
                progress.progress((i + 1) / len(selected_assets))
            
            if not market_data:
                st.error("No data found for selected assets.")
                return
            
            # 2. Run Engine
            try:
                metrics = BacktestEngine.run_portfolio_backtest(market_data, selected_strategy, **params)
                
                if not metrics:
                    st.warning("Backtest returned no metrics (insufficient data?).")
                    return
                
                # 3. Display Metrics
                st.subheader("Performance Metrics")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Return", f"{metrics['total_return']:.2%}")
                c2.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
                c3.metric("Max Drawdown", f"{metrics['max_drawdown']:.2%}")
                c4.metric("Volatility (Ann.)", f"{metrics['volatility']:.2%}")
                
                # 4. Plot Equity Curve
                st.subheader("Equity Curve")
                equity_df = pd.DataFrame({
                    'Strategy': metrics['equity_curve'],
                    'Benchmark (Equal Weight)': metrics['benchmark_curve']
                })
                
                fig = px.line(equity_df, title=f"Portfolio Value ({strategy_name})")
                st.plotly_chart(fig, use_container_width=True)
                
                # 5. Show Signal Heatmap (Bonus)
                with st.expander("🔎 Trade Signals Debugger", expanded=False):
                    # We can re-run strategy logic to get raw signals for visualization
                    # or update engine to return them. For now, let's just show returns
                    st.write("Daily Portfolio Returns:")
                    st.line_chart(metrics['daily_returns'])
                    
            except Exception as e:
                st.error(f"Backtest Error: {str(e)}")
                # st.exception(e)
