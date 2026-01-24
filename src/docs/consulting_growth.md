# Growth Factor Indicators

To capture the "Magnificent 7" effect, you need to measure **Expansion**. Here are the most effective metrics:

## 1. The Holy Trinity of Growth

### A. Revenue Growth (Top Line)
*   **Metric**: `Revenue Growth (Quarterly YoY)`
*   **Why**: It's the hardest to fake. You can massage earnings with accounting, but bringing in more cash from customers is real.
*   **Standard**: > 20% is "High Growth".

### B. EPS Growth (Bottom Line)
*   **Metric**: `Earnings Growth (Quarterly YoY)`
*   **Why**: Ultimately, stock prices follow earnings. 
*   **Warning**: Check if it's driven by *Buybacks* or *Cost Cutting*. Real growth comes from Revenue.

### C. Free Cash Flow Growth
*   **Metric**: `FCF Growth`
*   **Why**: The fuel for future reinvestment. Amazon famously minimized EPS for years to maximize FCF Growth.

## 2. Advanced / Quality Growth

### A. "Rule of 40" (SaaS / Tech Standard)
*   **Formula**: `Revenue Growth Rate + Free Cash Flow Margin`.
*   **Target**: > 40%.
*   **Logic**: It allows a company to be unprofitable IF it is growing insanely fast (e.g., growing 50% with -10% margin = 40).

### B. Forward PEG Ratio (Valuation Check)
*   **Formula**: `P/E Ratio / Future Growth Rate`.
*   **Target**: < 1.0 (Cheap), < 2.0 (Reasonable).
*   **Logic**: Paying 50x P/E is fine IF the company grows 50% a year (PEG = 1). Paying 20x P/E for 2% growth is a trap.

## 3. Implementation in Our Logic
We can add a **"Growth Score"** column:
1.  Fetch `Revenue Growth` and `Gross Margins`.
2.  Rank by `Revenue Growth`.
3.  Filter: **Peg Ratio < 2.0** (Don't buy bubbles).

## Recommended Strategy: GARP (Growth at Reasonable Price)
Instead of pure Growth (buying expensive hype), we buy the intersection of Growth + Value.
