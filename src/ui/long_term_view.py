import streamlit as st
import pandas as pd
import plotly.express as px
from src.engines.core_engine import CoreEngine

def run_analysis(tickers):
    """
    Executes the Smart Beta analysis and renders results.
    """
    engine = CoreEngine()
    with st.spinner("Fetching data and calculating factors... This may take a minute for the first run."):
        df = engine.rank_stocks(tickers)
    
    if df.empty:
        st.warning("No data found or all tickers failed.")
        return

    st.success("Analysis Complete")
    
    # Top Ranked
    st.subheader("Top Ranked Stocks (with TA Overlay)")
    st.dataframe(
        df[['ticker', 'composite_score', 'ta_action', 'trend_status', 'momentum_12m', 'roe', 'z_score', 'volatility', 'close']].head(10).style.format({
            'composite_score': '{:.2f}',
            'momentum_12m': '{:.2%}',
            'roe': '{:.2%}',
            'z_score': '{:.2f}',
            'volatility': '{:.2%}',
            'close': '${:.2f}'
        }).map(
            lambda x: 'color: green' if x == 'Buy (Trend)' or x == 'Buy (Support Bounce)' else 'color: red' if x == 'Sell / Avoid' else '',
            subset=['ta_action']
        ),
        width='stretch'
    )
    
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

def run_magic_formula_analysis(tickers):
    """
    Executes the Magic Formula analysis and renders results.
    """
    engine = CoreEngine()
    with st.spinner("Calculating Magic Formula Ranks..."):
        df = engine.rank_magic_formula(tickers)
        
    if df.empty:
        st.warning("No data found (Fundamentals might be missing).")
        return
        
    st.success("Magic Formula Calculation Complete")
    
    st.subheader("Top Ranked Stocks (Lowest Score is Best)")
    st.markdown("Score = Rank(ROC) + Rank(Earnings Yield)")
    
    # Format and show
    st.dataframe(df[['ticker', 'magic_score', 'roc', 'earnings_yield', 'close', 'method']].head(15).style.format({
        'roc': '{:.2%}',
        'earnings_yield': '{:.2%}',
        'close': '${:.2f}',
        'magic_score': '{:.0f}'
    }))
    
    st.subheader("Visualization: Quality vs Value")
    fig = px.scatter(
        df,
        x="roc",
        y="earnings_yield",
        color="magic_score",
        hover_name="ticker",
        title="Magic Formula: High ROC (Right) + High Yield (Top) = Best (Dark Blue)",
        labels={"roc": "Return on Capital (Quality)", "earnings_yield": "Earnings Yield (Value)"}
    )
    st.plotly_chart(fig, use_container_width=True)

def render(tickers):
    st.title("Long-Term Investment Strategies")
    
    # Ensure state initialization
    if 'active_lt_strategy' not in st.session_state:
        st.session_state['active_lt_strategy'] = None

    # Strategy Hub Layout
    col1, col2 = st.columns([1, 1])
    
    # Card 1: Multi-Factor Smart Beta
    with st.container():
        st.subheader("🌟 Multi-Factor Smart Beta")
        
        with st.expander("📖 Strategy Details: Philosophy & Methodology", expanded=True):
            st.markdown("""
            **核心哲学 (Philosophy)**: 
            并不是所有的股票都生而平等。历史数据证明，具备特定特征（因子）的股票长期能跑赢大盘。Smart Beta 就是通过系统性的规则，将被动投资（指数）与主动选股（因子）结合起来。
            
            **因子模型 (Factor Model)**:
            *   🚀 **Momentum (动量 - 40%)**: "强者恒强"。我们计算 12个月的累计收益率（跳过最近1个月）。过去一年表现最好的股票，同时也大概率在未来继续表现良好。
            *   💎 **Quality (质量 - 40%)**: "买得好不如买得对"。我们使用 **ROE (净资产收益率)** 作为核心指标，寻找具备持续盈利能力和护城河的公司。
            *   🛡️ **Low Volatility (低波 - 20%)**: "稳中求胜"。我们惩罚高波动率的股票。在市场动荡期，低波股票能提供更好的风险调整后收益。
            
            **适用场景 (Use Case)**:
            *   **核心持仓 (Core Holdings)**: 适合构建占据仓位 50%-80% 的压舱石组合。
            *   **中长期持有**: 建议持有周期为 **3个月 - 1年以上**。
            *   **季度轮动**: 建议每季度检查一次排名，剔除掉出前 20% 的股票。
            
            **技术叠加 (TA Overlay)**:
            尽管这是基本面策略，我们依然引入了 **SMA 200** 和 **Trend Check** 作为辅助，避免在长期下降趋势中买入"便宜的好公司" (Value Trap)。
            """)
        
        # Button Logic
        if st.button("Run Smart Beta Analysis", type="primary"):
            st.session_state['active_lt_strategy'] = 'smart_beta'
            
    # Card 2: Magic Formula
    with st.container():
        st.subheader("🔮 Greenblatt's Magic Formula")
        
        with st.expander("📖 Strategy Details: The Deep Value Engine", expanded=True):
            st.markdown("""
            **核心哲学 (Philosophy)**: 
            买股票就是买公司。既然如此，我们应该买 **"好公司" (Good)**，并且在 **"便宜的价格" (Cheap)** 买入。如果一家公司资本回报率高，且市场对其定价过低，这就是捡钱的机会。
            
            **因子模型 (Ranking Engine - Hybrid)**:
            *   **Strict Mode (优先)**: 使用 Greenblatt 原版公式 `EBIT/(EV)` 和 `EBIT/(Assets - Current Liab)`。
            *   **Fallback Mode (备用)**: 如果 EV 数据缺失，自动切换为 `1/PE` 和 `ROA`。
            
            1.  🏭 **Return on Capital**: 衡量公司利用资本赚钱的能力。
            2.  💰 **Earnings Yield**: 衡量你花钱买下公司后，每年能回本多少 (EBIT / Enterprise Value)。
            
            **适用场景 (Use Case)**:
            *   **逆向投资 (Contrarian)**: 专门寻找被市场错杀的优质股。
            *   **长期持有**: 书中建议持仓 **1年**，不仅能等到价值回归，还能享受长期资本利得税优惠。
            *   **心理挑战**: 这种策略选出来的股票通常都有"坏消息"缠身（否则不会便宜），需要极强的持币信心。
            """)
            
        if st.button("Run Magic Formula Analysis", type="primary"):
            st.session_state['active_lt_strategy'] = 'magic_formula'

    st.markdown("---")

    # Render Result if Active
    # Render Result if Active
    if st.session_state['active_lt_strategy'] == 'smart_beta':
        st.divider()
        st.header("📊 Smart Beta Analysis Results")
        run_analysis(tickers)
        
    elif st.session_state['active_lt_strategy'] == 'magic_formula':
        st.divider()
        st.header("🔮 Magic Formula Analysis Results")
        run_magic_formula_analysis(tickers)
