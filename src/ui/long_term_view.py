import streamlit as st
import pandas as pd
import plotly.express as px
from src.engines.stock_selection_engine import StockSelectionEngine


def run_analysis(tickers):
    """
    Executes the Smart Beta analysis and renders results.
    """
    engine = StockSelectionEngine()
    with st.spinner("Loading data from Local Database (Instant)..."):
        df = engine.rank_stocks(tickers)
    
    if df.empty:
        st.warning("No data found. Please go to 'Data Center' and run 'Batch Sync' first.")
        return

    st.success("Analysis Complete")
    
    # Top Ranked
    st.subheader("Top Ranked Stocks (with TA Overlay)")
    
    # Format Rank Change
    def format_change(x):
        if pd.isna(x): return "New"
        if x > 0: return f"⬆️ {int(x)}"
        if x < 0: return f"⬇️ {abs(int(x))}"
        return "➖"

    df['change_fmt'] = df['rank_change'].apply(format_change)
    
    # Initialize backtest_tickers if not present
    if 'backtest_tickers' not in st.session_state:
        st.session_state['backtest_tickers'] = []
        
    # Add Checkbox Column for Backtest Lab
    df['Add to Lab'] = df['ticker'].isin(st.session_state['backtest_tickers'])
    
    # Prepare Dataframe for Editor (Top 10)
    # We copy to avoid setting on a slice warning, though direct assignment above handles it usually.
    # Select columns including the new 'Add to Lab'
    display_cols = ['Add to Lab', 'ticker', 'change_fmt', 'composite_score', 'ta_action', 
                   'trend_status', 'momentum_12m', 'roe', 'z_score', 'volatility', 'close']
    
    df_display = df[display_cols].head(10).copy()

    # Configure Editor
    # We use st.data_editor with disabled columns for everything except "Add to Lab"
    edited_df = st.data_editor(
        df_display.style.format({
            'composite_score': '{:.2f}',
            'momentum_12m': '{:.2%}',
            'roe': '{:.2%}',
            'z_score': '{:.2f}',
            'volatility': '{:.2%}',
            'close': '${:.2f}'
        }).map(
            lambda x: 'color: green' if x == 'Buy (Trend)' or x == 'Buy (Support Bounce)' else 'color: red' if x == 'Sell / Avoid' else '',
            subset=['ta_action']
        ).map(
            lambda x: 'color: green' if "⬆️" in str(x) else 'color: red' if "⬇️" in str(x) else 'color: gray',
            subset=['change_fmt']
        ),
        column_config={
            "Add to Lab": st.column_config.CheckboxColumn(
                "Add to Backtest?",
                help="Check to add this stock to the Backtest Lab",
                default=False,
            ),
            "ticker": st.column_config.TextColumn("Ticker", disabled=True),
            "change_fmt": st.column_config.TextColumn("Rank Change", disabled=True),
            "composite_score": st.column_config.NumberColumn("Score", disabled=True),
            "ta_action": st.column_config.TextColumn("TA Action", disabled=True),
            "trend_status": st.column_config.TextColumn("Trend", disabled=True),
            "momentum_12m": st.column_config.NumberColumn("Momentum", disabled=True),
            "roe": st.column_config.NumberColumn("ROE", disabled=True),
            "z_score": st.column_config.NumberColumn("Z-Score", disabled=True),
            "volatility": st.column_config.NumberColumn("Volatility", disabled=True),
            "close": st.column_config.NumberColumn("Price", disabled=True),
        },
        disabled=display_cols[1:], # Disable all except the first one ('Add to Lab')
        hide_index=True,
        use_container_width=True,
        key="smart_beta_editor"
    )
    
    # Sync Logic
    # We compare the edited_df with the session state
    # Since edited_df ONLY contains the Top 10 (or whatever head(10) is),
    # we only sync tickers present in this view.
    
    if edited_df is not None:
        view_tickers = edited_df['ticker'].tolist()
        
        # Identify which ones are checked in the new view
        selected_in_view = edited_df[edited_df['Add to Lab'] == True]['ticker'].tolist()
        
        # Identify which ones are UNchecked in the new view
        unselected_in_view = edited_df[edited_df['Add to Lab'] == False]['ticker'].tolist()

        # Update Session State
        # 1. Add newly selected
        for t in selected_in_view:
            if t not in st.session_state['backtest_tickers']:
                st.session_state['backtest_tickers'].append(t)
        
        # 2. Remove newly unselected
        for t in unselected_in_view:
            if t in st.session_state['backtest_tickers']:
                st.session_state['backtest_tickers'].remove(t)
                
    # Feedback
    count = len(st.session_state['backtest_tickers'])
    if count > 0:
        st.caption(f"🧪 **Backtest Lab**: {count} stock(s) selected ({', '.join(st.session_state['backtest_tickers'])})")
    
    # Visualization
    st.subheader("Factor Map")
    st.info("💡 **Tip**: Select a stock in the table above to add it to **Backtest Lab**!")
    
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
    
    # Enable click events (view only)
    st.plotly_chart(fig, use_container_width=True)
    
    # Selection logic removed from chart
    
    # Detailed Table
    st.subheader("Full Rankings")
    st.dataframe(df)

def run_magic_formula_analysis(tickers):
    """
    Executes the Magic Formula analysis and renders results.
    """
    engine = StockSelectionEngine()
    with st.spinner("Calculating Magic Formula Ranks (Local DB)..."):
        df = engine.rank_magic_formula(tickers)
        
    if df.empty:
        st.warning("No data found. Please go to 'Data Center' and run 'Batch Sync' first.")
        return
        
    st.success("Magic Formula Calculation Complete")
    
    st.subheader("Top Ranked Stocks (Lowest Score is Best)")
    st.markdown("Score = Rank(ROC) + Rank(Earnings Yield)")
    
    # Format and show
    # Format and show
    def format_change(x):
        if pd.isna(x): return "New"
        if x > 0: return f"⬆️ {int(x)}"
        if x < 0: return f"⬇️ {abs(int(x))}"
        return "➖"

    df['change_fmt'] = df['rank_change'].apply(format_change)

    st.dataframe(df[['ticker', 'change_fmt', 'magic_score', 'roc', 'earnings_yield', 'close', 'method']].head(15).style.format({
        'roc': '{:.2%}',
        'earnings_yield': '{:.2%}',
        'close': '${:.2f}',
        'magic_score': '{:.0f}'
    }).map(
        lambda x: 'color: green' if "⬆️" in str(x) else 'color: red' if "⬇️" in str(x) else 'color: gray',
        subset=['change_fmt']
    ))
    
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

def run_garp_analysis(tickers):
    engine = StockSelectionEngine()
    with st.spinner("Loading Growth & PEG Data (Local DB)..."):
        df = engine.rank_garp(tickers)
        
    if df.empty:
        st.warning("No data found. Please go to 'Data Center' and run 'Batch Sync' first.")
        return
        
    st.success("GARP Analysis Complete")
    
    st.subheader("Top Growth Stocks (Value Adjusted)")
    st.dataframe(df.head(15).style.format({
        'growth': '{:.2%}',
        'peg': '{:.2f}',
        'roe': '{:.2%}',
        'close': '${:.2f}'
    }))
    
    st.subheader("Growth vs PEG Map")
    fig = px.scatter(
        df, x="growth", y="peg", color="garp_score", hover_name="ticker",
        title="Ideal Sector: Bottom Right (High Growth, Low PEG)",
        labels={"growth": "Revenue Growth", "peg": "PEG Ratio"}
    )
    # Add target box?
    fig.add_hrect(y0=0, y1=2.0, line_width=0, fillcolor="green", opacity=0.1)
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
            Smart Beta 是一种"增强型指数投资"。我们不买整个干草堆(指数)，而是只挑选其中最亮的金针(优质股)。
            
            **📊 如何解读结果 (How to Read Analysis)**:
            此策略会对所有股票进行打分排序，重点关注以下指标：
            *   **Composite Score (综合得分)**: **越高越好**。这是基于动量(40%)、质量(40%)和低波(20%)权重的加权标准分。
            *   **Momentum (动量)**:过去12个月的股价表现。数值越高，代表趋势越强。
            *   **ROE (净资产收益率)**: "巴菲特最爱的指标"。衡量公司用股东的钱赚钱的能力。>15% 为优秀。
            *   **Z-Score (破產风险)**: Altman Z-Score。>3.0 代表财务非常健康，<1.8 代表有破产风险。
            
            **操作建议**:
            1.  关注排名前 10 的股票。
            2.  检查 **TA Overlay** (技术面叠加)：避免买入处于 "Sell / Avoid" (下降趋势) 的股票，即使它很便宜。
            3.  **持有周期**: 3-12 个月 (中长期趋势)。
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
            以"好价格"买入"好公司"。这是价值投资大师 Joel Greenblatt 发明的神奇公式，长期年化回报惊人。
            
            **📊 如何解读结果 (How to Read Analysis)**:
            *   **Magic Score**: **越低越好**! (排名总和)。它是 "ROC排名" + "收益率排名" 的总和。第一名的总分最低。
            *   **ROC (资本回报率)**: 衡量公司"赚钱的效率"。越高越好。
            *   **Earnings Yield (收益率)**: 衡量"性价比"。类似市盈率倒数(E/P)，越高代表越便宜。
            
            **图表解读**:
            *   **右上角 (Dark Blue)**: 最佳区域。代表高ROC (好公司) 且 高Yield (便宜)。
            
            **操作建议**:
            *   **逆向思维**: 排名靠前的公司通常最近都有坏消息（所以才便宜）。需要极强的心理素质持有。
            *   **分散投资**: Greenblatt 建议持仓 20-30 只股票以分散个股风险。
            *   **持有周期**: 1年 (需忍受短期波动)。
            """)
            
        if st.button("Run Magic Formula Analysis", type="primary"):
            st.session_state['active_lt_strategy'] = 'magic_formula'

    # Card 3: GARP
    with st.container():
        st.subheader("🚀 GARP (Growth at Reasonable Price)")
        with st.expander("📖 Strategy Details: Catching the Next Star", expanded=True):
            st.markdown("""
            **核心哲学**:
            寻找还在高速成长期，但估值尚未泡沫化的股票。这是 Peter Lynch (彼得·林奇) 最爱的策略，专门捕捉 **Ten Baggers (十倍股)**。
            
            **📊 如何解读结果 (How to Read Analysis)**:
            此策略寻找 **PEG < 1.0 (或 < 2.0)** 的股票。
            *   **GARP Score**: **越低越好** (排名总和)。
            *   **PEG Ratio**: 市盈率相对盈利增长比率 (PE / Growth)。
                *   `< 1.0`: 严重低估 (Strong Buy)。
                *   `1.0 - 2.0`: 合理区间 (Buy/Hold)。
                *   `> 2.0`: 高估 (Avoid)。
            *   **Revenue Growth**: 这一年的营收增长率。必须 > 15% 才有爆发力。
            
            **图表解读**:
            *   **右下角**: 黄金区域 (高增长 + 低PEG)。这是我们要找的"漏网之鱼"。
            
            **风险提示**: 成长股波动极大，一旦增长不及预期，会有"双杀"风险 (EPS下降 + 估值下降)。
            """)
        if st.button("Run GARP Analysis", type="primary"):
            st.session_state['active_lt_strategy'] = 'garp'
            
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

    elif st.session_state['active_lt_strategy'] == 'garp':
        st.divider()
        st.header("🚀 GARP Analysis Results")
        run_garp_analysis(tickers)
