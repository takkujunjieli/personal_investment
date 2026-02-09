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

    if st.button("🚀 Run Backtest", type="primary"):
        if not selected_assets:
            st.warning("Please select at least one asset.")
            return

        with st.spinner(f"Simulating Strategy on {len(selected_assets)} assets..."):
            # Prepare to collect results
            all_results = []
            
            # Check for Analysis Span
            period = st.session_state.get('analysis_span', '1y')
            
            progress = st.progress(0)
            
            for i, ticker in enumerate(selected_assets):
                # 1. Fetch Data
                df = fetcher.fetch_data(ticker, period=period)
                if df.empty:
                    continue
                
                # 2. Run Single Asset Logic (Reusing Portfolio Logic on Single Asset)
                # We can mock a single-asset "portfolio" to reuse the engine, 
                # or better yet, just extract the calculation logic. 
                # For simplicity/robustness, we'll treat it as a 1-asset portfolio 
                # to leverage existing `run_portfolio_backtest`.
                market_data = {ticker: df}
                
                try:
                    metrics = BacktestEngine.run_portfolio_backtest(market_data, selected_strategy, **params)
                    
                    if metrics and 'equity_curve' in metrics:
                        # Convert equity curve to cumulative return % (Equity - 1)
                        # Equity starts at 1.0. 1.10 means 10% return.
                        equity_series = metrics['equity_curve']
                        cum_ret_series = (equity_series - 1) * 100 # In Percent
                        
                        # Create a temp df for this ticker
                        temp_df = pd.DataFrame({
                            'Date': cum_ret_series.index,
                            'Return (%)': cum_ret_series.values,
                            'Ticker': ticker,
                            # Constant metrics for hover
                            'Total Return': metrics['total_return'],
                            'Sharpe': metrics['sharpe_ratio'],
                            'Max Drawdown': metrics['max_drawdown']
                        })
                        all_results.append(temp_df)
                        
                except Exception as e:
                    st.error(f"Error backtesting {ticker}: {str(e)}")
                
                progress.progress((i + 1) / len(selected_assets))
            
            if not all_results:
                st.error("No valid backtest results generated.")
                return

            # Combine all results
            final_df = pd.concat(all_results, ignore_index=True)
            
            # 3. Plot Multi-Line Chart
            st.subheader("Performance Comparison")
            
            fig = px.line(
                final_df, 
                x="Date", 
                y="Return (%)", 
                color="Ticker",
                title=f"Strategy Performance: {strategy_name}",
                custom_data=['Ticker', 'Total Return', 'Sharpe', 'Max Drawdown']
            )
            
            # Customize Hover
            fig.update_traces(
                hovertemplate="<br>".join([
                    "<b>%{customdata[0]}</b>",
                    "Date: %{x|%Y-%m-%d}",
                    "Cum Return: %{y:.2f}%",
                    "Total Return: %{customdata[1]:.2%}",
                    "Sharpe Ratio: %{customdata[2]:.2f}",
                    "Max Drawdown: %{customdata[3]:.2%}"
                ])
            )
            
            fig.update_layout(hovermode="x unified") # Comparison mode
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Optional: Summary Table
            st.subheader("Metrics Summary")
            summary_data = []
            for res in all_results:
                # Take the first row (since metrics are constant columns)
                first_row = res.iloc[0]
                summary_data.append({
                    "Ticker": first_row['Ticker'],
                    "Total Return": f"{first_row['Total Return']:.2%}",
                    "Sharpe": f"{first_row['Sharpe']:.2f}",
                    "Max Drawdown": f"{first_row['Max Drawdown']:.2%}"
                })
            
            st.dataframe(pd.DataFrame(summary_data))
