# Professional Long-Term Strategies (Non-Momentum)

You asked for strategies with a **20-year track record** and **massive institutional adoption**. Here are the Top 3 alternatives to "Trend Following":

## 1. 🦈 Shareholder Yield (The "Cannibals")
*   **Adoption**: High (Indexes: S&P 500 Buyback Index, ETFs: PKW, SYLD).
*   **Logic**: Companies that distribute cash to shareholders via **Dividends** AND **Share Buybacks**.
    *   Buybacks are "Invisible Dividends". They reduce share count, artificially boosting EPS, forcing the P/E down and Price up.
*   **Performance (2010-2024)**: **Outperformed S&P 500**.
    *   This has been the dominant driver of the US Bull Market. Companies like **Apple**, **AutoZone**, and **O'Reilly** are "Cannibals" (they ate 30-50% of their own float).
*   **Why use it?**: It finds cash-rich companies that value their own stock.

## 2. 🛡️ Dividend Growth (The "Aristocrats")
*   **Adoption**: Massive (Indexes: S&P 500 Dividend Aristocrats, ETFs: NOBL). standard for Pension Funds.
*   **Logic**: Only buy companies that have **increased dividends for 25+ consecutive years**.
*   **Performance**: **Lower Volatility, Similar Return**.
    *   They rarely "Moon" like Nvidia, but they rarely crash 80% like Zoom.
*   **Why use it?**: Defensive layer. Defensive against recession.

## 3. ⚖️ GARP (Growth At Reasonable Price)
*   **Adoption**: The "Active Manager" Standard (Peter Lynch, Fidelity).
*   **Logic**: Buy High Growth, but Cap the P/E.
    *   Metric: **PEG Ratio** (PE / Growth Rate). Perfect is < 1.0.
*   **Performance**: Cyclical. Crushes it during "Soft Landings".
*   **Why use it?**: To catch the "Next Big Thing" before it becomes too expensive.

## Recommendation: Implement "Shareholder Yield"
If you want a strategy that works specifically well in the **modern US tax environment** (where buybacks > dividends), "Shareholder Yield" is the quantitative king.

### Implementation Logic
1.  **Net Buyback Yield**: `(Shares_Year_Ago - Shares_Now) / Shares_Now`.
2.  **Dividend Yield**: `Dividend / Price`.
3.  **Total Yield**: `Buyback Yield + Dividend Yield`.
4.  **Rank**: Top 10% highest Total Yield + Positive Free Cash Flow.
