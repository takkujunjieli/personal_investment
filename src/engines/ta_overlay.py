import pandas as pd
import numpy as np

class TechnicalAnalysis:
    @staticmethod
    def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds basic technical indicators to the dataframe.
        Expects 'close' column.
        """
        if df.empty or 'close' not in df.columns:
            return df
        
        # 1. Moving Averages (Trend)
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        # 2. Volume Analysis
        if 'volume' in df.columns:
            df['vol_sma_20'] = df['volume'].rolling(window=20).mean()
            # Relative Volume (RVOL) = Current Volume / Average Volume
            # Avoid division by zero
            df['rvol'] = df['volume'] / df['vol_sma_20'].replace(0, 1)

        # 3. MACD (Momentum)
        # EMA 12, EMA 26
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd_line'] = ema12 - ema26
        df['macd_signal'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd_line'] - df['macd_signal']
        
        return df

    @staticmethod
    def check_trend_setup(df: pd.DataFrame) -> dict:
        """
        Returns a dictionary of trend status based on the latest data.
        """
        if df.empty or len(df) < 200:
            return {'trend': 'Unknown', 'ta_signal': 'Wait/No Data'}
            
        current = df.iloc[-1]
        
        # Macro Trend: Price vs SMA 200
        trend = "Bullish" if current['close'] > current['sma_200'] else "Bearish"
        
        # Short-term Momentum: MACD
        macd_bullish = current['macd_line'] > current['macd_signal']
        
        # Pullback Setup: Price close to SMA 20 (within 2%)
        dist_sma20 = (current['close'] - current['sma_20']) / current['sma_20']
        near_support = abs(dist_sma20) < 0.02
        
        signal = "Neutral"
        if trend == "Bullish":
            if near_support:
                signal = "Buy (Support Bounce)"
            elif macd_bullish:
                signal = "Buy (Trend)"
        elif trend == "Bearish":
            if macd_bullish:
                signal = "Cautious (Rebound)"
            else:
                signal = "Sell / Avoid"
                
        return {
            'trend': trend,
            'macd': 'Bull' if macd_bullish else 'Bear',
            'ta_signal': signal,
            'dist_sma200': (current['close'] - current['sma_200']) / current['sma_200']
        }
