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
        Post-Earnings Announcement Drift Scanner (Daily Only).
        Uses Daily data to spot Gap Ups (Open vs Prev Close).
        """
        # Merge defaults with provided params
        config = self.pead_strat.default_params.copy()
        config.update(params)
        
        gap_threshold = config.get('gap_pct', 0.02)
        min_rvol = config.get('min_rvol', 1.5) # New Param
        
        candidates = []
        for ticker in tickers:
            # We need enough history for 20-day Volume SMA
            daily_df = self.market.fetch_data(ticker, period="2mo")
            if daily_df.empty or len(daily_df) < 22: # 20 for SMA + 2 for gap
                continue
            
            # Helper for indicators
            daily_df = TechnicalAnalysis.add_indicators(daily_df)
            
            today = daily_df.iloc[-1]
            yesterday = daily_df.iloc[-2]
            
            # 1. Calc Gap: Today Open vs Yesterday Close
            prev_close = yesterday['close']
            today_open = today['open']
            
            if prev_close == 0: continue
            
            gap_pct = (today_open - prev_close) / prev_close
            
            # 2. Filter: Gap > Threshold
            if gap_pct > gap_threshold:
                # 3. Volume Check: RVOL > Threshold
                # We want high relative volume to confirm institutional interest
                rvol = today.get('rvol', 1.0) # Default to 1 if missing for some reason
                
                if rvol > min_rvol:
                    # 4. Strength Check: Price is holding?
                    # Condition: Current Price (Close) > Open * 0.99
                    current_price = today['close']
                    
                    if current_price > (today_open * 0.99):
                        trend_setup = TechnicalAnalysis.check_trend_setup(daily_df)
                        
                        candidates.append({
                            'ticker': ticker,
                            'signal': 'PEAD (Gap + Vol)',
                            'gap_pct': gap_pct,
                            'rvol': round(rvol, 2),
                            'current_return': (current_price - prev_close)/prev_close,
                            'price': current_price,
                            'time': 'Daily',
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
        Condition: VIX is high AND Stock drops > VaR 95% AND High Volume (Capitulation).
        """
        # Merge defaults
        config = self.rev_strat.default_params.copy()
        config.update(params)
        
        lookback = config.get('lookback', 252)
        percentile = config.get('percentile', 0.05)
        min_rvol = config.get('min_rvol', 2.0) # Panic selling volume threshold
        
        candidates = []
        
        # 1. Check VIX Context
        current_vix, vix_ma = self.get_market_sentiment()
        is_high_vol = current_vix > 20 or current_vix > (vix_ma * 1.1)
        
        for ticker in tickers:
            df = self.market.fetch_data(ticker, period="1y")
            if df.empty or len(df) < 50:
                continue
            
            # Add Volume Indicators
            df = TechnicalAnalysis.add_indicators(df)
            
            today = df.iloc[-1]
            current_price = today['close']
            rvol = today.get('rvol', 0)
            
            # VaR (95%) - Historical Simulation
            returns = df['close'].pct_change().dropna()
            var_95 = returns.quantile(percentile) 
            today_ret = returns.iloc[-1]
            
            # Logic: PRICE DROP > VaR Threshold (Tail Event) AND High Volume
            if today_ret < var_95:
                # Secondary Check: Is it a high volume washout?
                # If volume is low, it might just be a bleed, not a capitulation bottom.
                if rvol > min_rvol:
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
                        'rvol': round(rvol, 2),
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
