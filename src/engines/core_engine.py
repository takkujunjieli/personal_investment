import pandas as pd
import numpy as np
from src.data.market_data import MarketDataFetcher
from src.data.fundamental_data import FundamentalDataFetcher
from src.engines.ta_overlay import TechnicalAnalysis
from sklearn.preprocessing import StandardScaler

class CoreEngine:
    def __init__(self):
        self.market = MarketDataFetcher()
        self.fund = FundamentalDataFetcher()

    def calculate_factors(self, tickers: list) -> pd.DataFrame:
        """
        Calculates Value, Quality, and Momentum factors for a list of tickers.
        Returns a DataFrame with raw factor values.
        """
        data = []
        
        for ticker in tickers:
            print(f"Processing {ticker}...")
            # 1. Momentum (Market Data)
            # 12-month return, RSI
            price_df = self.market.fetch_data(ticker, period="2y")
            if price_df.empty:
                continue
            
            # Simple Momentum: 1-year return
            current_price = price_df['close'].iloc[-1]
            one_year_ago = price_df['close'].asfreq('B').shift(252).iloc[-1] # approx
            
            # Handle missing data
            if pd.isna(one_year_ago):
                # Try to get the first available if < 1 year
                one_year_ago = price_df['close'].iloc[0]
            
            momentum_12m = (current_price / one_year_ago) - 1
            
            # Simple Volatility (Inverse of 20d StdDev)
            volatility = price_df['close'].pct_change().tail(20).std()
            
            # 2. Value & Quality (Fundamental Data)
            # We need to fetch fundamentals first if not present
            self.fund.fetch_fundamentals(ticker)
            self.fund.fetch_fundamentals(ticker)
            metrics = self.fund.get_latest_metrics(ticker, ['Net Income', 'Stockholders Equity', 'Total Equity Gross Minority Interest'])
            
            # We need Market Cap for Value (Price * Shares). 
            # yfinance provides marketCap in 'info' but we are avoiding slow API calls for every single thing.
            # Approximation: Net Income / Price? No, that's E/P. 
            # Let's rely on basic accounting ratios if we can, or just use Price relative to Book.
            
            # P/B Ratio = Market Cap / Total Equity = Price / (Total Equity / Shares)
            # This is hard without share count. 
            # Alternative: ROI (Return on Investment) or ROE (Return on Equity)
            # Quality: ROE = Net Income / Total Equity
            
            net_income = metrics.get('Net Income')
            # Try multiple keys for Equity
            equity = metrics.get('Stockholders Equity') or metrics.get('Total Equity Gross Minority Interest')
            
            roe = np.nan
            if net_income and equity and equity != 0:
                roe = net_income / equity
                
            # Value proxy: For now, we might lack Shares Outstanding in our light DB.
            # We will use "Price vs 52w High" as a value/reversion proxy or rely on pre-computed P/E if we had it.
            # Let's stick to Factors we can compute: Momentum, Volatility, ROE.
            # To get P/E or P/B properly, we need Shares Outstanding. 
            # I'll update MarketDataFetcher to try and get 'shares' from info if crucial, 
            # but for now let's build the framework with what we have.
            
            data.append({
                'ticker': ticker,
                'momentum_12m': momentum_12m,
                'volatility': volatility,
                'roe': roe,
                'close': current_price
            })
            
        return pd.DataFrame(data)

    def rank_stocks(self, tickers: list, weights: dict = None) -> pd.DataFrame:
        """
        Ranks stocks based on weighted Z-scores of factors AND adds TA overlay.
        """
        if weights is None:
            # ... existing weights ...
            weights = {
                'momentum_12m': 0.4,
                'roe': 0.4,
                'volatility': -0.2 
            }
            
        df = self.calculate_factors(tickers)
        if df.empty:
            return df
        
        print("DEBUG: Raw Factor Data Frame:")
        print(df[['ticker', 'momentum_12m', 'roe', 'volatility']])
        
        # Normalize (Z-Score)
        scaler = StandardScaler()
        score_col = np.zeros(len(df))
        
        for factor, weight in weights.items():
            if factor not in df.columns:
                continue
            values = df[factor].fillna(df[factor].mean()).values.reshape(-1, 1)
            score_col += scaler.fit_transform(values).flatten() * weight
            
        df['composite_score'] = score_col
        df.sort_values('composite_score', ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        # --- TA OVERLAY ---
        # For the top 20 stocks, we calculate TA Signal
        # This prevents fetching full history for everything if list is huge
        ta_signals = []
        for index, row in df.iterrows():
            # We need full history for MA200 (at least 200 bars)
            price_df = self.market.fetch_data(row['ticker'], period="2y")
            
            # Smart Check: If cache is too short despite asking for 2y, Force Download
            if len(price_df) < 250: # 1 trading year approx
                 print(f"Cache too short for {row['ticker']} ({len(price_df)}), forcing full history...")
                 price_df = self.market.fetch_data(row['ticker'], period="2y", force_download=True)

            price_df = TechnicalAnalysis.add_indicators(price_df)
            setup = TechnicalAnalysis.check_trend_setup(price_df)
            
            ta_signals.append({
                'trend_status': setup['trend'], # Bullish/Bearish (SMA200)
                'ta_action': setup['ta_signal'] # Buy/Wait
            })
            
        ta_df = pd.DataFrame(ta_signals)
        df = pd.concat([df, ta_df], axis=1)
        
        return df
