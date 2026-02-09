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
        # Add Buy & Hold as a "Virtual" Strategy Option
        available_strats = ["Buy & Hold"] + list(strategies.keys())
        
        selected_strategy_names = st.multiselect(
            "Select Strategy(ies)", 
            available_strats, 
            default=["Buy & Hold"],
            key="bt_strategies"
        )

    fetcher = MarketDataFetcher()
    
    # 3. Strategy Configuration (Dynamic)
    st.subheader("Strategy Parameters")
    
    # Render parameters for each selected strategy (excluding Buy & Hold)
    active_strategies = {}
    strategy_params = {}
    
    for name in selected_strategy_names:
        if name in strategies:
            active_strategies[name] = strategies[name]
            # Use expander to organize params if multiple strategies or just general tidiness
            with st.expander(f"⚙️ {name} Parameters", expanded=True):
                params = active_strategies[name].default_params.copy()
                cols = st.columns(len(params))
                for i, (key, default_val) in enumerate(params.items()):
                    with cols[i]:
                        # Create unique key for widget
                        widget_key = f"{name}_{key}"
                        if isinstance(default_val, int):
                            params[key] = st.number_input(key, value=default_val, step=1, key=widget_key)
                        elif isinstance(default_val, float):
                            params[key] = st.number_input(key, value=default_val, step=0.1, key=widget_key)
                strategy_params[name] = params
                
    st.markdown("---")

    if st.button("🚀 Run Backtest", type="primary"):
        if not selected_assets:
            st.warning("Please select at least one asset.")
            return

        with st.spinner(f"Simulating..."):
            # Check for Analysis Span
            analysis_span = st.session_state.get('analysis_span', '1y')
            
            # Map span to a longer fetch period for warmup
            # We want to fetch MORE data than needed so indicators (SMA200 etc) are ready at start of span.
            fetch_map = {
                '1mo': '6mo', '3mo': '1y', '6mo': '2y', 
                'ytd': '2y', '1y': '2y', '3y': '5y', 
                '5y': '10y', 'max': 'max'
            }
            fetch_period = fetch_map.get(analysis_span, '5y')
            
            # Calculate Cutoff Date for Visuals & Metrics
            cutoff_date = None
            today = pd.Timestamp.now().normalize()
            if analysis_span == '1mo': cutoff_date = today - pd.Timedelta(days=30)
            elif analysis_span == '3mo': cutoff_date = today - pd.Timedelta(days=90)
            elif analysis_span == '6mo': cutoff_date = today - pd.Timedelta(days=180)
            elif analysis_span == 'ytd': cutoff_date = pd.Timestamp(today.year, 1, 1)
            elif analysis_span == '1y': cutoff_date = today - pd.Timedelta(days=365)
            elif analysis_span == '3y': cutoff_date = today - pd.Timedelta(days=365*3)
            elif analysis_span == '5y': cutoff_date = today - pd.Timedelta(days=365*5)
            # max: None
            
            all_results = []
            progress = st.progress(0)
            
            # Helper to slice & rebase
            def process_results(series_ret, name):
                # 1. Slice
                if cutoff_date and not series_ret.empty:
                    series_ret = series_ret[series_ret.index >= cutoff_date]
                
                if series_ret.empty: return None, None
                
                # 2. Recalculate Metrics for this specific window
                local_metrics = BacktestEngine.calculate_metrics(series_ret)
                
                # 3. Rebase Equity Curve (Start at 0%)
                cum_ret = (1 + series_ret).cumprod()
                
                # Normalize so first point is 0% change relative to start of window
                # Actually, (1+r).cumprod() starts from first return.
                # To normalize visually diff-style: (Value_t / Value_0) - 1
                # But cum_ret is already growth factor. 
                # value_series = cum_ret / cum_ret.iloc[0] * 1000 (base)
                # simpler: cum_ret_pct = (cum_ret / cum_ret.iloc[0] - 1) 
                
                cum_ret_rebased = (cum_ret / cum_ret.iloc[0]) - 1
                
                return cum_ret_rebased * 100, local_metrics

            # Fetch QQQ Benchmark
            # User wants "Default only buy and hold" text, but QQQ is a benchmark. 
            # We will keep QQQ as a separate distinct line for reference.
            qqq_df_raw = fetcher.fetch_data("QQQ", period=fetch_period)
            if not qqq_df_raw.empty:
                qqq_ret = qqq_df_raw['close'].pct_change().fillna(0)
                
                q_curve, q_metrics = process_results(qqq_ret, "QQQ")
                
                if q_curve is not None:
                    qqq_plot_df = pd.DataFrame({
                        'Date': q_curve.index,
                        'Return (%)': q_curve.values,
                        'Legend Name': 'QQQ (Benchmark)', # Distinguish from Ticker
                        'Ticker': 'QQQ',
                        'Strategy': 'Benchmark',
                        'Total Return': q_metrics['total_return'],
                        'Sharpe': q_metrics['sharpe_ratio'],
                        'Max Drawdown': q_metrics['max_drawdown']
                    })
                    all_results.append(qqq_plot_df)

            # Collect Marker Data
            buy_markers = []
            sell_markers = []

            for i, ticker in enumerate(selected_assets):
                # 1. Fetch Data with Extended Period
                df = fetcher.fetch_data(ticker, period=fetch_period)
                if df.empty:
                    continue
                
                market_data = {ticker: df}
                
                # 2. Iterate Selected Strategies
                for strat_name in selected_strategy_names:
                    try:
                        metrics = {}
                        is_bh = strat_name == "Buy & Hold"
                        
                        # Get daily returns first
                        raw_daily_ret = None
                        raw_weights = None
                        
                        if is_bh:
                            # Buy & Hold Logic
                            raw_daily_ret = df['close'].pct_change().fillna(0)
                        else:
                            # Strategy Logic
                            strat_instance = active_strategies[strat_name]
                            s_params = strategy_params[strat_name]
                            strat_res = BacktestEngine.run_portfolio_backtest(market_data, strat_instance, **s_params)
                            if strat_res and 'daily_returns' in strat_res:
                                raw_daily_ret = strat_res['daily_returns']
                                raw_weights = strat_res.get('positions', None)
                        
                        if raw_daily_ret is not None:
                            # Process Results (Slice & Rebase)
                            vis_curve, vis_metrics = process_results(raw_daily_ret, strat_name)
                            
                            if vis_curve is not None:
                                legend_name = f"{ticker} ({strat_name})"
                                
                                temp_df = pd.DataFrame({
                                    'Date': vis_curve.index,
                                    'Return (%)': vis_curve.values,
                                    'Legend Name': legend_name,
                                    'Ticker': ticker,
                                    'Strategy': strat_name,
                                    'Total Return': vis_metrics['total_return'],
                                    'Sharpe': vis_metrics['sharpe_ratio'],
                                    'Max Drawdown': vis_metrics['max_drawdown']
                                })
                                all_results.append(temp_df)
                                
                                # Signals / Markers processing (Sliced)
                                if not is_bh and raw_weights is not None:
                                    weights = raw_weights
                                    # weights is a DF with ticker columns. Get this ticker's series.
                                    if ticker in weights.columns:
                                        w_series = weights[ticker]
                                        
                                        # Slice weights to match visual window
                                        if cutoff_date:
                                            w_series = w_series[w_series.index >= cutoff_date]
                                            
                                        # Detect changes
                                        diff = w_series.diff().fillna(0)
                                        
                                        # Buy: diff > 0
                                        buys = diff[diff > 0].index
                                        # Sell: diff < 0
                                        sells = diff[diff < 0].index
                                        
                                        # We need Y-values (Returns) at these dates
                                        # Align dates with vis_curve
                                        buy_y = vis_curve.loc[vis_curve.index.intersection(buys)]
                                        sell_y = vis_curve.loc[vis_curve.index.intersection(sells)]
                                        
                                        if not buy_y.empty:
                                            buy_markers.append({
                                                'x': buy_y.index,
                                                'y': buy_y.values,
                                                'name': legend_name 
                                            })
                                        if not sell_y.empty:
                                            sell_markers.append({
                                                'x': sell_y.index,
                                                'y': sell_y.values,
                                                'name': legend_name
                                            })

                    except Exception as e:
                        st.error(f"Error processing {ticker} - {strat_name}: {str(e)}")
                
                progress.progress((i + 1) / len(selected_assets))
            
            if not all_results:
                st.error("No valid results generated.")
                return

            # Combine all results
            final_df = pd.concat(all_results, ignore_index=True)
            
            # 3. Plot Multi-Line Chart
            st.subheader("Performance Comparison")
            
            fig = px.line(
                final_df, 
                x="Date", 
                y="Return (%)", 
                color="Legend Name",
                title=f"Multi-Strategy Backtest",
                custom_data=['Legend Name', 'Total Return', 'Sharpe', 'Max Drawdown']
            )
            
            # Add Markers
            import plotly.graph_objects as go
            for i, m in enumerate(buy_markers):
                show_leg = (i == 0)
                fig.add_trace(go.Scatter(
                    x=m['x'], y=m['y'],
                    mode='markers',
                    marker=dict(symbol='arrow-up', color='green', size=9),
                    name="Buy Signal",
                    legendgroup="buy_signal",
                    showlegend=show_leg,
                    hoverinfo='skip' 
                ))
                
            for i, m in enumerate(sell_markers):
                show_leg = (i == 0)
                fig.add_trace(go.Scatter(
                    x=m['x'], y=m['y'],
                    mode='markers',
                    marker=dict(symbol='arrow-down', color='red', size=9),
                    name="Sell Signal",
                    legendgroup="sell_signal",
                    showlegend=show_leg,
                    hoverinfo='skip'
                ))
            
            # Customize Hover
            fig.update_traces(
                hovertemplate="<br>".join([
                    "<b>%{customdata[0]}</b>",
                    "Date: %{x|%Y-%m-%d}",
                    "Cum Return: %{y:.2f}%",
                    "<hr>",
                    "Total Ret: %{customdata[1]:.2%}",
                    "Sharpe: %{customdata[2]:.2f}",
                    "Max DD: %{customdata[3]:.2%}"
                ]),
                selector=dict(type='scatter', mode='lines') # Only apply to lines
            )
            
            fig.update_layout(hovermode="closest") 
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Optional: Summary Table
            st.subheader("Metrics Summary")
            summary_data = []
            # We want one row per (Ticker, Strategy) combination
            # Group by Legend Name to get unique entries
            unique_results = final_df.drop_duplicates(subset=['Legend Name'])
            
            for _, row in unique_results.iterrows():
                summary_data.append({
                    "Name": row['Legend Name'],
                    # "Ticker": row['Ticker'],
                    # "Strategy": row['Strategy'],
                    "Total Return": f"{row['Total Return']:.2%}",
                    "Sharpe": f"{row['Sharpe']:.2f}",
                    "Max Drawdown": f"{row['Max Drawdown']:.2%}"
                })
            
            st.dataframe(pd.DataFrame(summary_data))
