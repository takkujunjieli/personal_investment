import pandas as pd
import numpy as np
from src.data.market_data import MarketDataFetcher
from src.engines.ta_overlay import TechnicalAnalysis
import yfinance as yf
from datetime import datetime, timedelta

class SatelliteEngine:
    def __init__(self):
        self.market = MarketDataFetcher()

    def scan_pead(self, tickers: list) -> pd.DataFrame:
        """
        Post-Earnings Announcement Drift Scanner.
        Uses Intraday data to spot true Gap Ups including Pre-Market action.
        """
        candidates = []
        for ticker in tickers:
            # We first check daily for a rough signal to avoid API spamming
            # If daily shows a big move, we dive into intraday
            daily_df = self.market.fetch_data(ticker, period="5d")
            if daily_df.empty or len(daily_df) < 2:
                continue
            
            today = daily_df.iloc[-1]
            yesterday = daily_df.iloc[-2]
            
            # Rough Check: Did it move today?
            daily_change = (today['close'] - yesterday['close']) / yesterday['close']
            
            if abs(daily_change) > 0.02: # If > 2% move, let's investigate the microstructure
                
                # Fetch 5-minute data with pre-market
                intra = self.market.fetch_intraday(ticker, period="2d", interval="15m")
                if intra.empty:
                    continue
                    
                # Logic: Compare Yesterday's Regular Close vs Today's Pre-Market High/Open
                # Or simply: Look at the first bar of today vs last bar of yesterday
                
                # Split by day
                dates = intra.index.to_series().dt.date.unique()
                if len(dates) < 2:
                    continue
                    
                today_date = dates[-1]
                yesterday_date = dates[-2]
                
                today_bars = intra[intra.index.date == today_date]
                yesterday_bars = intra[intra.index.date == yesterday_date]
                
                if today_bars.empty or yesterday_bars.empty:
                    continue
                    
                prev_close = yesterday_bars['close'].iloc[-1]
                today_open = today_bars['open'].iloc[0] # This includes pre-market if present
                
                gap_pct = (today_open - prev_close) / prev_close
                
                # Filter: Gap > 2% AND Price Holding (Current > Open * 0.98)
                current_price = intra['close'].iloc[-1]
                
                if gap_pct > 0.02 and current_price > (today_open * 0.98):
                    # TA Check: Is it above SMA20? (Trend alignment)
                    daily_with_ta = TechnicalAnalysis.add_indicators(daily_df.copy())
                    trend_setup = TechnicalAnalysis.check_trend_setup(daily_with_ta)
                    
                    candidates.append({
                        'ticker': ticker,
                        'signal': 'PEAD (Intraday Confirmed)',
                        'gap_pct': gap_pct,
                        'current_return': (current_price - prev_close)/prev_close,
                        'price': current_price,
                        'time': intra.index[-1].strftime('%H:%M'),
                        'ta_trend': trend_setup['trend']
                    })
                
        return pd.DataFrame(candidates)

    def get_market_sentiment(self):
        """
        Fetches VIX to determine if market is in fear mode.
        """
        try:
            vix = self.market.fetch_data("^VIX", period="5d")
            if not vix.empty:
                current_vix = vix['close'].iloc[-1]
                vix_ma = vix['close'].mean()
                return current_vix, vix_ma
        except:
            pass
        return 0, 0

    def scan_reversal(self, tickers: list) -> pd.DataFrame:
        """
        VaR Breach Scanner based on Liquidity Crisis logic.
        Condition: VIX is high AND Stock drops > VaR 95%.
        """
        candidates = []
        
        # 1. Check VIX Context
        current_vix, vix_ma = self.get_market_sentiment()
        # Threshold: VIX > 20 is a common proxy for "Fear", or looking for a spike
        is_high_vol = current_vix > 20 or current_vix > (vix_ma * 1.1)
        
        # Note: If VIX is low, we warn the user that these might be idiosyncratic risks, not forced selling.
        
        for ticker in tickers:
            df = self.market.fetch_data(ticker, period="1y")
            if df.empty or len(df) < 50:
                continue
            
            current_price = df['close'].iloc[-1]
            
            # VaR (95%) - Historical Simulation
            # Look at 1-year distribution of returns
            returns = df['close'].pct_change().dropna()
            
            # VaR 95% is the 5th percentile (e.g., -0.03)
            var_95 = returns.quantile(0.05) 
            today_ret = returns.iloc[-1]
            
            # Logic: PRICE DROP > VaR Threshold (e.g. Drop -5% when VaR is -3%)
            # This indicates a "Tail Event"
            
            if today_ret < var_95:
                # We found a VaR Breach.
                # Now classify it:
                signal_type = "Idiosyncratic Crash (Risk!)"
                confidence = "Low"
                
                if is_high_vol:
                    signal_type = "Liquidity Driver (VIX Spike)"
                    confidence = "High (Quality on Sale)"
                
                candidates.append({
                    'ticker': ticker,
                    'signal': signal_type,
                    'confidence': confidence,
                    'drop': today_ret,
                    'var_95': var_95,
                    'price': current_price,
                    'vix_context': round(current_vix, 2)
                })
                
        return pd.DataFrame(candidates)
