from abc import ABC, abstractmethod
import pandas as pd
import numpy as np

class Strategy(ABC):
    """
    Abstract base class for all investment strategies.
    A Strategy encapsulates both Selection and Timing logic.
    """
    
    @abstractmethod
    def run(self, market_data: dict[str, pd.DataFrame], **params) -> pd.DataFrame:
        """
        Executes the strategy on the provided market data.
        
        Args:
            market_data: A dictionary where key is ticker and value is the OHLCV DataFrame.
                         DataFrames should all be aligned by index (Date).
            **params: Strategy-specific parameters.

        Returns:
            pd.DataFrame: A DataFrame of Target Weights (0.0 to 1.0).
                          Index = Date
                          Columns = Tickers
                          Values = Portfolio Weight
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def default_params(self) -> dict:
        pass


class SmaCrossStrategy(Strategy):
    """
    Simple Trend Follow:
    Long (100% / N) if Short MA > Long MA.
    Neutral (0%) otherwise.
    """
    @property
    def name(self):
        return "SMA Trend Following"

    @property
    def default_params(self):
        return {'short_window': 20, 'long_window': 200}

    def run(self, market_data: dict, short_window=20, long_window=200) -> pd.DataFrame:
        signals = pd.DataFrame(index=list(market_data.values())[0].index, columns=market_data.keys())
        
        for ticker, df in market_data.items():
            if len(df) < long_window:
                signals[ticker] = 0.0
                continue
                
            close = df['close']
            short_ma = close.rolling(window=short_window).mean()
            long_ma = close.rolling(window=long_window).mean()
            
            # 1.0 if Short > Long, else 0.0
            signals[ticker] = np.where(short_ma > long_ma, 1.0, 0.0)
            
        # Equal weight normalization (optional, here we just return 1/0 signals per asset)
        # If user wants portfolio level weighting, we can divide by N active assets
        # For now, let's keep it simple: 1.0 means "Invested in this asset"
        return signals

class RsiMeanReversionStrategy(Strategy):
    """
    Mean Reversion:
    Long if RSI < Buy Threshold.
    Exit if RSI > Sell Threshold.
    """
    @property
    def name(self):
        return "RSI Mean Reversion"

    @property
    def default_params(self):
        return {'rsi_period': 14, 'buy_threshold': 30, 'sell_threshold': 70}

    def run(self, market_data: dict, rsi_period=14, buy_threshold=30, sell_threshold=70) -> pd.DataFrame:
        signals = pd.DataFrame(index=list(market_data.values())[0].index, columns=market_data.keys())
        
        for ticker, df in market_data.items():
            if len(df) < rsi_period:
                signals[ticker] = 0.0
                continue
            
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            sig = pd.Series(np.nan, index=df.index)
            sig[rsi < buy_threshold] = 1.0
            sig[rsi > sell_threshold] = 0.0
            
            sig.ffill(inplace=True)
            sig.fillna(0.0, inplace=True)
            signals[ticker] = sig
            
        return signals
