import streamlit as st
import pandas as pd
import plotly.express as px
from src.data.market_data import MarketDataFetcher
from src.engines.backtest_engine import BacktestEngine, strategy_sma_trend, strategy_rsi_reversion

def render(tickers):
    st.header("Backtest Lab 🧪")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        ticker = st.selectbox("Select Asset", tickers, key="bt_ticker")
    with col2:
        strategy_name = st.selectbox("Select Strategy", ["SMA Trend Following", "RSI Mean Reversion"])
    
    fetcher = MarketDataFetcher()
    
    # Strategy Config
    params = {}
    if strategy_name == "SMA Trend Following":
        st.subheader("Parameters")
        c1, c2 = st.columns(2)
        params['short_window'] = c1.slider("Short MA", 5, 100, 20)
        params['long_window'] = c2.slider("Long MA", 50, 300, 200)
        strategy_choice = strategy_sma_trend
        
    elif strategy_name == "RSI Mean Reversion":
        st.subheader("Parameters")
        c1, c2, c3 = st.columns(3)
        params['rsi_period'] = c1.number_input("RSI Period", 2, 30, 14)
        params['buy_threshold'] = c2.slider("Buy Threshold", 10, 50, 30)
        params['sell_threshold'] = c3.slider("Sell Threshold", 50, 90, 70)
        strategy_choice = strategy_rsi_reversion

    if st.button("Run Backtest", type="primary"):
        with st.spinner("Simulating..."):
            # Fetch full history
            df = fetcher.fetch_data(ticker, period="5y")
            if df.empty:
                st.error("No data.")
                return
            
            # Run Engine
            res = BacktestEngine.run(df, strategy_choice, **params)
            
            # Display Metrics
            m = res
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Return", f"{m['total_return']:.2%}")
            c2.metric("Sharpe Ratio", f"{m['sharpe_ratio']:.2f}")
            c3.metric("Max Drawdown", f"{m['max_drawdown']:.2%}")
            
            # Plot
            equity_df = pd.DataFrame({
                'Strategy': res['equity_curve'],
                'Buy & Hold': (1 + df['close'].pct_change()).cumprod()
            })
            
            st.markdown("### Equity Curve")
            st.line_chart(equity_df)
            
            # --- OPTIMIZATION (Bonus) ---
            with st.expander("🤖 Grid Search Optimization"):
                if st.button("Find Best Parameters"):
                    with st.spinner("Optimizing..."):
                        if strategy_name == "SMA Trend Following":
                            grid = {
                                'short_window': [10, 20, 50],
                                'long_window': [100, 150, 200, 250]
                            }
                        else:
                            grid = {
                                'rsi_period': [7, 14, 21],
                                'buy_threshold': [20, 30, 40],
                                'sell_threshold': [60, 70, 80]
                            }
                        
                        opt_results = BacktestEngine.optimize(df, strategy_choice, grid)
                        best = opt_results[0]
                        st.success(f"Best Sharpe: {best['metrics']['sharpe_ratio']:.2f}")
                        st.write("Best Parameters:", best['params'])
                        
                        # Show Top 5
                        top5 = pd.DataFrame([
                            {**r['params'], 'Sharpe': r['metrics']['sharpe_ratio'], 'Return': r['metrics']['total_return']} 
                            for r in opt_results[:5]
                        ])
                        st.dataframe(top5)
