# Risk/Reward Ratio (R/R) Calculator

## The Formula
$$ R/R = \frac{|Target Price - Entry Price|}{|Entry Price - Stop Loss Price|} $$

## Case Study: Shorting RXRX
*   **Scenario A: Shorting Stock**
    *   **Entry**: $8.00
    *   **Target** (Thesis: Dilution to death): $4.00 (Profit $4.00)
    *   **Stop Loss** (Risk: Good news spike): $12.00 (Loss $4.00)
    *   **Calculation**: $4 / 4 = 1.0$.
    *   **Verdict**: **UNINVESTABLE**. You are risking $1 to make $1. Professionals usually demand at least 2:1 or 3:1.

*   **Scenario B: Buying Put Options (Strike $7, Exp 6 months)**
    *   **Cost (Risk)**: $1.50 per share (The Premium).
    *   **Target (Stock goes to $4)**: Option Intrinsic Value = $3.00. Profit = $3.00 - $1.50 = $1.50? No, usually Volatility expansion adds more. Let's say potential value $4.50. Net Profit $3.00.
    *   **Ratio**: $3.00 (Reward) / $1.50 (Risk) = 2:1.
    *   **Target (Stock goes to $0)**: Option Value = $7.00. Net Profit = $5.50.
    *   **Ratio**: $5.50 / $1.50 = 3.6:1.
    *   **Verdict**: **BETTER**.

## Position Sizing (Rule of Thumb)
If R/R is 2:1, you need to be right >33% of the time to break even.
If R/R is 3:1, you only need to be right >25% of the time.

**Kelly Criterion (Simplified)**:
$$ f = \frac{p(b+1) - 1}{b} $$
*   $f$ = % of capital to bet
*   $b$ = R/R Ratio (e.g., 3.0)
*   $p$ = Probability of winning (e.g., 0.4)

## Implementation Advice
I can add a **"Trade Calculator"** to the Sidebar so you can input these 3 numbers (Entry, Target, Stop) and instantly see if a trade is worth taking before you click buy/sell.
