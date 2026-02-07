import pandas as pd
import numpy as np
import itertools
from src.engines.strategy_registry import Strategy

class BacktestEngine:
    """
    Portfolio Backtesting Engine.
    Supports multi-asset strategies.
    """
    
    @staticmethod
    def calculate_metrics(daily_returns: pd.Series):
        """
        Computes Sharpe, Max Drawdown, Total Return.
        daily_returns: Series of portfolio returns.
        """
        if daily_returns.empty:
            return {}
            
        total_return = (1 + daily_returns).prod() - 1
        
        # Annualized Sharpe (Assuming 252 trading days, Rf=0 for simplicity)
        sharpe = 0
        if daily_returns.std() > 0:
            sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
            
        # Max Drawdown
        cumulative = (1 + daily_returns).cumprod()
        peak = cumulative.cummax()
        drawdown = (cumulative - peak) / peak
        max_drawdown = drawdown.min()
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'volatility': daily_returns.std() * np.sqrt(252)
        }

    @staticmethod
    def run_portfolio_backtest(market_data: dict[str, pd.DataFrame], strategy: Strategy, **params):
        """
        Runs a portfolio backtest.
        
        Args:
            market_data: {ticker: DataFrame}
            strategy: Strategy instance
            **params: Strategy parameters
        
        Returns:
            dict: Metrics and Equity Curve
        """
        tickers = list(market_data.keys())
        if not tickers:
            return {}

        # 1. Align Data (Index)
        # We assume all dfs are roughly aligned, but let's get a common index
        common_index = market_data[tickers[0]].index
        for t in tickers[1:]:
            common_index = common_index.union(market_data[t].index)
        common_index = common_index.sort_values()
        
        # 2. Get Signals from Strategy (0 or 1 usually)
        # Strategy returns a DataFrame of target weights/signals
        raw_signals = strategy.run(market_data, **params)
        
        # Reindex signals to common index just in case
        raw_signals = raw_signals.reindex(common_index).fillna(0)
        
        # 3. Portfolio Construction (Equal Weight among active signals)
        # If Signal is 1, we hold it.
        # Weight = 1 / (Sum of Signals)
        # If user selected 10 stocks, and strategy says buy 5, each gets 20%.
        
        active_counts = raw_signals.sum(axis=1)
        weights = raw_signals.div(active_counts, axis=0).fillna(0)
        
        # 4. Calculate Portfolio Returns
        # Portfolio Return = Sum(Weight_i * Return_i)
        
        # Build Returns DataFrame
        returns_df = pd.DataFrame(index=common_index)
        for t in tickers:
            # Shifted because we enter at Close (or Open next day). 
            # Simplified: Signal today -> Return tomorrow.
            market_ret = market_data[t]['close'].pct_change()
            market_ret = market_ret.reindex(common_index).fillna(0)
            returns_df[t] = market_ret
            
        # Shift weights: Weights determined at T close apply to T+1 return
        portfolio_returns = (weights.shift(1) * returns_df).sum(axis=1)
        
        # 5. Metrics
        metrics = BacktestEngine.calculate_metrics(portfolio_returns)
        metrics['equity_curve'] = (1 + portfolio_returns).cumprod()
        metrics['daily_returns'] = portfolio_returns
        
        # Benchmark (Equal Weight of Universe)
        benchmark_ret = returns_df.mean(axis=1)
        metrics['benchmark_curve'] = (1 + benchmark_ret).cumprod()
        
        return metrics

# Legacy support if needed, or can be removed

