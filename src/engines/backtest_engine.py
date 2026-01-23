import pandas as pd
import numpy as np
import itertools

class BacktestEngine:
    """
    A fast, vectorized backtesting engine for single-asset strategies.
    """
    
    @staticmethod
    def calculate_metrics(daily_returns):
        """
        Computes Sharpe, Max Drawdown, Total Return.
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
            'max_drawdown': max_drawdown
        }

    @staticmethod
    def run(df: pd.DataFrame, strategy_func, **params):
        """
        Runs a strategy on a DataFrame.
        df: Must contain 'close'
        strategy_func: Function(df, **params) -> returns Series of signals (1, 0, -1)
        """
        data = df.copy()
        
        # 1. Generate Signals
        # Signal = Position to hold at End of Day.
        # We assume we enter at Close of Signal Day (or Open of Next Day).
        # Vectorized standardized: Signal today executes at Close today (simplified)
        # Realistically: Signal calculated at Close, Trade at Next Open.
        # Let's use: Returns = Shifted Signal * Next Day Return.
        
        data['signal'] = strategy_func(data, **params)
        
        # 2. Calculate Strategy Returns
        # Strategy Return = Signal(t-1) * Return(t)
        # If Signal is 1 (Long) on Monday Close, we capture Tuesday's change.
        data['market_return'] = data['close'].pct_change()
        data['strategy_return'] = data['signal'].shift(1) * data['market_return']
        
        # Filter for trade period
        data.dropna(inplace=True)
        
        metrics = BacktestEngine.calculate_metrics(data['strategy_return'])
        metrics['equity_curve'] = (1 + data['strategy_return']).cumprod()
        
        return metrics

    @staticmethod
    def optimize(df: pd.DataFrame, strategy_func, param_grid: dict):
        """
        Grid search optimization.
        param_grid: {'window': [20, 50], 'threshold': [30, 70]}
        """
        keys, values = zip(*param_grid.items())
        combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
        
        results = []
        for params in combinations:
            metrics = BacktestEngine.run(df, strategy_func, **params)
            results.append({
                'params': params,
                'metrics': metrics
            })
            
        # Sort by Sharpe Ratio descending
        results.sort(key=lambda x: x['metrics']['sharpe_ratio'], reverse=True)
        return results

# --- STRATEGIES ---

def strategy_sma_trend(df, short_window=50, long_window=200):
    """
    Golden Cross Strategy:
    Long (1) if Short MA > Long MA
    Neutral (0) otherwise (or Short (-1) if desired)
    """
    short_ma = df['close'].rolling(window=short_window).mean()
    long_ma = df['close'].rolling(window=long_window).mean()
    
    signal = np.where(short_ma > long_ma, 1.0, 0.0)
    return pd.Series(signal, index=df.index)

def strategy_rsi_reversion(df, rsi_period=14, buy_threshold=30, sell_threshold=70):
    """
    Mean Reversion:
    Long (1) if RSI < Buy Threshold
    Close (0) if RSI > Sell Threshold
    """
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Logic: 
    # If RSI < 30 -> Enter Long (1)
    # If RSI > 70 -> Exit (0)
    # Else -> Hold previous position (ffill)
    
    signal = pd.Series(np.nan, index=df.index)
    signal[rsi < buy_threshold] = 1.0
    signal[rsi > sell_threshold] = 0.0
    
    # Fill forward: Hold position until exit signal
    signal.ffill(inplace=True)
    signal.fillna(0.0, inplace=True)
    
    return signal
