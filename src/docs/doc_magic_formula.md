# Strategy Documentation: Greenblatt's Magic Formula

## 1. Philosophy: The Deep Value Engine
Created by hedge fund manager Joel Greenblatt, this strategy attempts to automate the buying process of Warren Buffett: **"Buy wonderful companies at fair prices."**

It combines two rankings:
1.  **Metric A (Cheapness)**: Earnings Yield. How much does this business earn relative to its price?
2.  **Metric B (Quality)**: Return on Capital. How efficiently does this business use its assets?

## 2. Implementation Details (Current System)

### Hybrid Data Model
We use a **Hybrid Approach** to handle data limitations in the Yahoo Finance Free tier.

#### A. Strict Mode (Ideal)
Used when `EBIT`, `Enterprise Value` components are fully available.
*   **Earnings Yield** = $ \frac{EBIT}{Market Cap + Debt - Cash} $
*   **Return on Capital** = $ \frac{EBIT}{Total Assets - Current Liabilities} $

#### B. Proxy Mode (Fallback)
Used when data is missing.
*   **Earnings Yield** = $ \frac{1}{PE Ratio} $ (Using Diluted EPS / Price)
*   **Return on Capital** = $ ROA $ (Net Income / Total Assets)

## 3. Current Parameters
*   **Universe**: User defined Watchlist.
*   **Ranking**: Sum of Ranks (Lower score is better).
*   **Rebalance**: Recommended Annually.

## 4. Path to Professionalization (Refinement Roadmap)

The current implementation is a good "screener," but a rigorous quantitative strategy requires more filters:

### A. Financial & Utility Exclusion
*   **Adjustment**: **Exclude Banks, Insurance, and Utilities.**
*   **Reason**: Concepts like "EBIT" and "Working Capital" do not apply standardly to banks (whose "inventory" is money). Their high leverage makes EV distorted.

### B. Accounting Checks (The "Fraud" Filter)
*   **Adjustment**: Check **Accruals** (Net Income - Free Cash Flow).
*   **Reason**: If Net Income is high but Cash Flow is low, the company might be "stuffing the channel" or using aggressive accounting. High Accruals = Low Quality, regardless of ROIC.

### C. Look-Back vs Look-Forward
*   **Adjustment**: Greenblatt uses TTM (Trailing Twelve Months). However, markets price the *future*.
*   **Refinement**: Use **Forward Earnings Yield** (Analyst Consensus Estimates for Next Year EBIT / Current EV). This helps avoid "Value Traps" where historical earnings are high but the business is dying.

### D. Minimum Market Cap
*   **Adjustment**: Filter out Micro-caps (< $50M).
*   **Reason**: Magic Formula works best on small-caps, but micro-caps often have illiquidity costs that eat up the theoretical alpha.

## 5. When to use?
*   **Bear Markets**: Value strategies often shine when the growth bubble bursts.
*   **vs Smart Beta**: Magic Formula is "Mean Reversion" (buying beaten down stocks). Smart Beta is often "Trend Following" (buying winners). Holding both diversifies your "Factor Risk".
