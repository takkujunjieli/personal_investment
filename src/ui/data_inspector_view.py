import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.data.market_data import MarketDataFetcher
from src.engines.ta_overlay import TechnicalAnalysis
import pandas as pd
import numpy as np

def calculate_extra_indicators(df):
    """
    Helper to calc Bollinger, RSI which might not be in basic TA overlay yet.
    """
    # SMA is already in TA overlay
    
    # Bollinger Bands (20, 2)
    sma20 = df['close'].rolling(window=20).mean()
    std20 = df['close'].rolling(window=20).std()
    df['bb_upper'] = sma20 + (std20 * 2)
    df['bb_lower'] = sma20 - (std20 * 2)
    
    # RSI (14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df

def render(tickers):
    st.header("Interactive Technical Analysis 🕯️")
    
    fetcher = MarketDataFetcher()
    
    # --- CONTROLS ---
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        ticker = st.selectbox("Select Ticker", tickers)
    with col2:
        period = st.selectbox("Timeframe", ["3mo", "6mo", "1y", "2y", "5y"], index=2)
    with col3:
        st.write("") # Spacer
        if st.button("Load / Refresh Data", type="primary", use_container_width=True):
             with st.spinner(f"Fetching data for {ticker}..."):
                df = fetcher.fetch_data(ticker, period=period)
                if not df.empty:
                    # Pre-calculate common indicators to ensure readiness
                    df = TechnicalAnalysis.add_indicators(df)
                    df = calculate_extra_indicators(df)
                    st.session_state['inspector_df'] = df
                    st.session_state['inspector_ticker'] = ticker
                else:
                    st.error("No data found.")

    # --- RENDER IF DATA EXISTS ---
    if 'inspector_df' in st.session_state and not st.session_state['inspector_df'].empty:
        df = st.session_state['inspector_df']
        current_ticker = st.session_state.get('inspector_ticker', ticker)
        
        st.markdown(f"### Analysis: {current_ticker}")
        
        # Toggles Row
        cols = st.columns(6)
        show_sma = cols[0].checkbox("SMA", value=False)
        show_bb = cols[1].checkbox("Bollinger", value=False)
        show_volume = cols[2].checkbox("Volume", value=True)
        show_macd = cols[3].checkbox("MACD", value=False)
        show_rsi = cols[4].checkbox("RSI", value=False)
        
        # --- PLOTTING ---
        rows = 1
        row_heights = [0.7] # Main chart dominates
        specs = [[{"secondary_y": False}]]
        
        if show_volume:
            rows += 1
            row_heights.append(0.15)
            specs.append([{"secondary_y": False}])
            
        if show_macd or show_rsi:
            rows += 1
            row_heights.append(0.15)
            specs.append([{"secondary_y": False}])
        
        # Normalize heights
        total_h = sum(row_heights)
        row_heights = [r/total_h for r in row_heights]
        
        fig = make_subplots(
            rows=rows, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03, 
            row_heights=row_heights
        )
        
        # 1. Candlestick (Row 1)
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            name='OHLC'
        ), row=1, col=1)
        
        # Overlays
        if show_sma:
            colors = {'sma_20': 'orange', 'sma_50': 'blue', 'sma_200': 'purple'}
            for window in [20, 50, 200]:
                col_name = f'sma_{window}'
                if col_name in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df.index, y=df[col_name], 
                        mode='lines', name=f'SMA {window}',
                        line=dict(color=colors.get(col_name, 'gray'), width=1)
                    ), row=1, col=1)
                    
        if show_bb:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['bb_upper'], mode='lines', name='BB Upper',
                line=dict(color='gray', width=1, dash='dash')
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=df.index, y=df['bb_lower'], mode='lines', name='BB Lower', 
                line=dict(color='gray', width=1, dash='dash'),
                fill='tonexty'
            ), row=1, col=1)

        current_row = 2
        
        # 2. Volume
        if show_volume:
            colors = ['red' if row['open'] - row['close'] >= 0 else 'green' for index, row in df.iterrows()]
            fig.add_trace(go.Bar(
                x=df.index, y=df['volume'], name='Volume', marker_color=colors 
            ), row=current_row, col=1)
            current_row += 1
            
        # 3. Oscillators
        if show_macd:
            fig.add_trace(go.Scatter(x=df.index, y=df['macd_line'], name='MACD', line=dict(color='blue')), row=current_row, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['macd_signal'], name='Signal', line=dict(color='orange')), row=current_row, col=1)
            fig.add_trace(go.Bar(x=df.index, y=df['macd_hist'], name='Hist'), row=current_row, col=1)
            fig.update_yaxes(title_text="MACD", row=current_row, col=1)
            
        elif show_rsi:
            fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], name='RSI', line=dict(color='purple')), row=current_row, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=current_row, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=current_row, col=1)
            fig.update_yaxes(title_text="RSI", range=[0, 100], row=current_row, col=1)

        fig.update_layout(
            height=800 if (show_volume or show_macd or show_rsi) else 600,
            hovermode='x unified',
            xaxis_rangeslider_visible=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("View Raw Data"):
            st.dataframe(df.tail(20).style.format("{:.2f}"))
