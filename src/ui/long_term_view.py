import streamlit as st
import pandas as pd
import plotly.express as px
from src.engines.core_engine import CoreEngine

def render(tickers):
    st.title("Long-Term Strategy (Smart Beta)")
    st.markdown("Returns ranking based on **Momentum**, **Quality (ROE)**, and **Low Volatility**.")
    
    if st.button("Run Core Analysis"):
        engine = CoreEngine()
        with st.spinner("Fetching data and calculating factors... This may take a minute for the first run."):
            df = engine.rank_stocks(tickers)
        
        if df.empty:
            st.warning("No data found or all tickers failed.")
            return

        st.success("Analysis Complete")
        
        # Top Ranked
        st.subheader("Top Ranked Stocks (with TA Overlay)")
        st.dataframe(df[['ticker', 'composite_score', 'ta_action', 'trend_status', 'momentum_12m', 'roe', 'volatility', 'close']].head(10).style.format({
            'composite_score': '{:.2f}',
            'momentum_12m': '{:.2%}',
            'roe': '{:.2%}',
            'volatility': '{:.2%}',
            'close': '${:.2f}'
        }).applymap(
            lambda x: 'color: green' if x == 'Buy (Trend)' or x == 'Buy (Support Bounce)' else 'color: red' if x == 'Sell / Avoid' else '',
            subset=['ta_action']
        ))
        
        # Visualization
        st.subheader("Factor Map")
        df["composite_score_abs"] = df["composite_score"].fillna(0).abs()
        fig = px.scatter(
            df, 
            x="roe", 
            y="momentum_12m", 
            size="composite_score_abs", 
            color="composite_score", 
            hover_name="ticker",
            hover_data={
                "composite_score_abs": False, # Hide the abs value
                "composite_score": ':.2f',
                "roe": ':.2%',
                "momentum_12m": ':.2%',
                "volatility": ':.2%',
                "ta_action": True,
                "trend_status": True
            },
            title="Quality (ROE) vs Momentum (Color=Score, Size=Score Magnitude)"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed Table
        st.subheader("Full Rankings")
        st.dataframe(df)
