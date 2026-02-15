# ⚠️ Project Deprecation Notice

**This project is no longer actively maintained.**

## Overview
This was a Personal Investment Dashboard built with Streamlit, Python, and yfinance. It provided tools for:
-   Viewing financial data (Data Center)
-   Developing strategies (Strategy Lab)
-   Backtesting strategies (Backtest Lab)
-   Screening stocks

## Reason for Deprecation
After a thorough analysis comparing this local project with professional platforms like QuantConnect, it has been decided to deprecate the local backtesting and execution engines in favor of more robust cloud-based solutions.

Below is the detailed analysis report supporting this decision.

---

# Comparison: Local Project vs QuantConnect

## Executive Summary
**Verdict:** The current local project is excellent for **data visualization, hypothesis generation, and educational purposes**, but it lacks the robustness required for serious **algorithmic trading and accurate backtesting**.

If your goal is to *find* ideas and *manually* trade them, this project is valuable. If your goal is to *automate* trading or *accurately* verify a strategy's edge, QuantConnect is significantly superior.

## Detailed Comparison

| Feature | Local Project (Current) | QuantConnect (LEAN) |
| :--- | :--- | :--- |
| **Data Quality** | **Low/Medium** (`yfinance`). Prone to unadjusted data issues, missing delisted stocks (**Survivorship Bias**), and API rate limits. | **High**. Professional grade, adjusted for splits/divs, and includes delisted stocks (Crucial for avoiding survivorship bias). |
| **Backtesting Engine** | **Vectorized (Pandas)**. Very fast for simple logic. <br>❌ Impossible to test complex order types (Limits, Stops). <br>❌ No slippage or transaction costs modeling. <br>❌ "Close-to-Close" execution assumption is unrealistic. | **Event-Driven**. Simulates every tick/minute. <br>✅ Supports Limit, Stop, Trailing Stop orders. <br>✅ Realistic slippage, fees, and margin modeling. <br>✅ Accurate execution logic. |
| **Universe Selection** | **Static/Manual**. You define lists (e.g. S&P500). <br>❌ Static lists ignore historical changes (e.g. TSLA wasn't in S&P500 5 years ago). | **Dynamic**. "Top 500 Liquid Stocks". <br>✅ Automatically updates universe daily based on historical constituents. |
| **Strategy Development** | **Flexible (Python)**. Use any library (`streamlit`, `scikit-learn`) version you want. Fast iteration loop. | **Structured (Python/C#)**. Must follow QC API. Slower feedback loop (cloud backtest queue). Strict library versions. |
| **Infrastructure** | **Local**. Limited by your RAM/CPU. Data storage management is your responsibility. | **Cloud**. Scalable. Massive data library instantly available (Options, Futures, Crypto). |
| **Cost** | **Free** (Time intensive). | **Freemium**. Free tier is good, but live trading and advanced features cost money ($10-20/mo+). |
| **Privacy** | **100% Private**. Code and data stay on your machine. | **Cloud Hosted**. Code lives on QC servers (unless using LEAN CLI locally). |

## Key Gaps in Current Project

1.  **Survivorship Bias**: Your backtests only run on stocks currently existing. This artificially inflates performance (you never backtest on companies that went bankrupt).
2.  **Execution Realism**: The `BacktestEngine` assumes you can buy at yesterday's Close or today's Open with zero slippage. In reality, PEAD strategies (catching gaps) are highly sensitive to execution speed and liquidity.
3.  **Data Maintenance**: You are manually maintaining a `sqlite` database. Over time, `yfinance` breaks, data gets corrupted, and proper maintenance becomes a chore.

## Unique Value of Local Project ("Existence Necessity")

Despite the downsides, this project **does** have unique value:

1.  **Custom UI / Dashboard**: QuantConnect has a fixed UI. Your Streamlit app allows you to build custom workflows (e.g., "Strategy Lab" vs "Backtest Lab") tailored exactly to your mental model.
2.  **Rapid Visual Analysis**: Viewing charts, drawing overlays, and interactively filtering stocks is much faster locally than running a backtest to plot a chart on QC.
3.  **No Vendor Lock-in**: You own the code.

## Recommendation

**Hybrid Approach:**

1.  **Keep the Local App for "Idea Generation"**: Use it to scan for setups (Screening), visualize market breadth, and monitor your watchlists. It is a "Research Sandbox".
2.  **Move "Backtesting" to QuantConnect**: Do not trust the local `BacktestEngine` for performance verification. If you find a strategy you like locally (e.g. PEAD), code it in QuantConnect to verify it against real data and realistic execution.
3.  **Manual Execution**: If you trade manually, the local app is fine for generating signals. If you want to *auto-trade*, you MUST migrate to a robust engine like QC or interactive brokers API directly (but that requires rebuilding an execution engine).
