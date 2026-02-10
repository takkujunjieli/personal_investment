import pandas as pd
import numpy as np
from src.data.market_data import MarketDataFetcher
from src.engines.ta_overlay import TechnicalAnalysis
import yfinance as yf
from datetime import datetime, timedelta
from src.engines.strategy_registry import PeadStrategy, LiquidityCrisisStrategy, SentimentContrarianStrategy

class MarketTimingEngine:
    def __init__(self):
        self.market = MarketDataFetcher()
        self.pead_strat = PeadStrategy()
        self.rev_strat = LiquidityCrisisStrategy()
        self.sent_strat = SentimentContrarianStrategy()

    def scan_pead(self, tickers: list, **params) -> pd.DataFrame:
        """
        Post-Earnings Announcement Drift Scanner.
        Uses Intraday data to spot true Gap Ups including Pre-Market action.
        """
        # Merge defaults with provided params
        config = self.pead_strat.default_params.copy()
        config.update(params)
        
        gap_threshold = config.get('gap_pct', 0.02)
        
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
            
            if abs(daily_change) > gap_threshold: # If > Threshold move, let's investigate the microstructure
                
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
                
                # Filter: Gap > Threshold AND Price Holding (Current > Open * 0.98)
                current_price = intra['close'].iloc[-1]
                
                if gap_pct > gap_threshold and current_price > (today_open * 0.98):
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

    def scan_reversal(self, tickers: list, **params) -> pd.DataFrame:
        """
        VaR Breach Scanner based on Liquidity Crisis logic.
        Condition: VIX is high AND Stock drops > VaR 95%.
        """
        # Merge defaults
        config = self.rev_strat.default_params.copy()
        config.update(params)
        
        lookback = config.get('lookback', 252)
        percentile = config.get('percentile', 0.05)
        
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
            var_95 = returns.quantile(percentile) 
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
                    
                # Store extra info including VaR used
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

    def fetch_fear_greed_index(self):
        """
        Fetches the latest Fear & Greed Index from CNN.
        Returns: score (float), rating (str), timestamp (str)
        """
        try:
            import requests
            from datetime import datetime
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            # We fetch a recent start date to ensure we get the latest data point
            # Just fetched "graphdata" usually returns full history? Not sure, but "graphdata/DATE" returns from DATE.
            # Let's try to fetch just the latest index. 
            # Actually, let's use the one that worked in tests: graphdata/{recent_date}
            
            start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
            url = f"https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{start_date}"
            
            r = requests.get(url, headers=headers, timeout=5)
            r.raise_for_status()
            data = r.json()
            
            if 'fear_and_greed' in data:
                latest = data['fear_and_greed']
                return latest.get('score'), latest.get('rating'), latest.get('timestamp')
        except Exception as e:
            print(f"Error fetching FGI: {e}")
            return None, None, None
            
        return None, None, None

    def scan_sentiment(self, **params):
        """
        Scans current market sentiment.
        """
        # Merge defaults
        config = self.sent_strat.default_params.copy()
        config.update(params)
        
        buy_threshold = config.get('buy_threshold', 25)
        sell_threshold = config.get('sell_threshold', 75)
        
        score, rating, timestamp = self.fetch_fear_greed_index()
        
        if score is None:
            return {"error": "Could not fetch data"}
            
        signal = "NEUTRAL"
        action = "Hold / Normal Allocation"
        color = "gray"
        
        if score < buy_threshold:
            signal = "EXTREME FEAR"
            action = "BUY / Aggressive Allocation"
            color = "green"
        elif score > sell_threshold:
            signal = "EXTREME GREED"
            action = "SELL / Hedge / Defensive"
            color = "red"
            
        return {
            "score": score,
            "rating": rating,
            "signal": signal,
            "action": action,
            "color": color,
            "timestamp": timestamp
        }
