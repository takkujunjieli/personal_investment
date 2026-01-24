# 策略详解: Crisis Alpha (VaR Breach + VIX Spike)

## 1. 策略哲学 (Philosophy)
这个策略不再是简单的 "跌多了买"，而是基于 **由流动性危机引发的错杀**。
*   **机构风控机制**: 大型对冲基金和机构都有严格的 VaR (Value at Risk) 风控模型。
*   **强制减仓 (Forced Deleveraging)**: 当市场波动率 (VIX) 飙升时，资产的 VaR 会突破阈值。为了合规，风控部门会强制交易员减仓 (Sell anything liquid)。
*   **机会**: 这种抛售通常不分青红皂白，导致 **高质量、流动性好的大盘股** (Quality Large Caps) 被错杀。我们要做的，就是充当"最后贷款人"，以折扣价买入这些优质资产。

---

## 5. Path to Professionalization (Refinement Roadmap)

### A. Gamma Exposure (GEX) & Dark Pools
*   **Concept**: When Market Makers are "Short Gamma", they are forced to sell as markets drop, accelerating the crash.
*   **Refinement**: Only take crisis signals when **Net GEX is Negative**. This confirms the mathematical necessity of volatility expansion. (Requires Option metrics data).
*   **DIX (Dark Index)**: High dark pool buying during a crash indicates "Smart Money" is absorbing the liquidity dump.

### B. Correlation Filters
*   **Refinement**: Check **Implied Correlation**.
*   In a true Liquidity Crisis, Correlation -> 1.0. Everything is sold to raise cash (Gold, Bonds, Stocks).
*   If Correlation is low, it might just be a specific sector issue (e.g., Oil crash), not a systemic liquidity event.

### C. Time-Stop (Temporal Stop Loss)
*   **Refinement**: Reversal trades should work *fast*.
*   **Rule**: If the bounce doesn't happen within **3 Days**, exit. Do not turn a "trade" into an "investment" just because you are underwater.

### D. Bond Market Signals
*   **Refinement**: Watch **HYG (High Yield Bonds)**. If Stocks are crashing but HYG is stable, it's a fake-out. If HYG is crashing, the credit market is stressed -> Real Crisis -> Quality stocks are mispriced.

## 2. 核心逻辑 (Trading Logic)

### A. 市场环境过滤器 (Market Regime)
*   **Indicator**: `VIX (CBOE Volatility Index)`
*   **Condition**: `VIX > 20` (恐惧区间) OR `VIX > 1.5 * 20-Day MA` (波动率瞬间飙升)
*   *意义*: 只有在恐慌时刻，机构才会被迫不计成本地卖出。平静市场下的下跌通常是基本面变差，不能买。

### B. 个股信号 (Stock Signal)
*   **Target**: 仅限 **高质量大盘股** (Quality Mega Caps)。垃圾股跌了可能就真完了。
*   **Signal**: `Today Return < VaR 95%`
    *   例如，某股票历史日波动分布显示，95%的情况下跌幅不超过 3%。今天突然跌了 5%。
    *   结合 VIX 飙升，我们判断这是 "被动抛售" 造成的。

---

## 3. 具体执行 (Execution)

### 进场 (Entry)
1.  监控 VIX 指数，确认市场处于 "Stress" 状态。
2.  扫描 Universe 中跌幅超过自身 `VaR 95%` 的股票。
3.  **二次过滤**: 剔除有重大个股利空 (Earnings Miss, Fraud) 的股票。只买 "无辜躺枪" 的。

### 离场 (Exit)
*   **均值回归**: 当价格反弹回 Bollinger Band 中轨，或 VIX 回落时卖出。
*   此策略通常持仓时间极短 (1-3天)，博取流动性恢复带来的反弹。

> [!IMPORTANT]
> **Why Quality Matters**: 在流动性危机中，垃圾股可能会因为融姿断裂而归零。只有像 AAPL, MSFT 这种现金流充裕的巨头，才能在风暴过后确定性地反弹。
