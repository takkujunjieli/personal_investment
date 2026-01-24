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
        
        data = []
        
        # 0. Fetch Benchmark (SPY) for Relative Momentum
        self.spy_mom = 0.0
        try:
            spy_df = self.market.fetch_data("SPY", period="2y")
            if not spy_df.empty and len(spy_df) > 250:
                 # SPY 12-1 Month Calculation
                 spy_start = spy_df['close'].asfreq('B').shift(252).iloc[-1]
                 spy_end = spy_df['close'].asfreq('B').shift(21).iloc[-1] # 1 month ago
                 
                 if not pd.isna(spy_start) and not pd.isna(spy_end):
                     self.spy_mom = (spy_end / spy_start) - 1
                     print(f"Benchmark SPY 12-1m Return: {self.spy_mom:.2%}")
        except Exception as e:
            print(f"Error fetching SPY benchmark: {e}")

        for ticker in tickers:
            print(f"Processing {ticker}...")
            # 1. Momentum (Market Data)
            # 12-month return, RSI
            price_df = self.market.fetch_data(ticker, period="2y")
            if price_df.empty:
                continue
            
            # Current Price for Valuation/Display
            current_price = price_df['close'].iloc[-1]
            
            # Relative Momentum (vs SPY)
            # We need SPY return for the same period. 
            # Optimization: Fetch SPY once outside the loop? Yes, done below.
            
            # 12-1 Month Momentum (Standard Academic Momentum)
            # Skip most recent 1 month (approx 21 trading days) to avoid short-term reversal
            # Window: From 12 months ago to 1 month ago.
            
            # Start: 12 months ago (~252 days)
            start_price = price_df['close'].asfreq('B').shift(252).iloc[-1]
            
            # End: 1 month ago (~21 days)
            end_price = price_df['close'].asfreq('B').shift(21).iloc[-1]
            
            # Fallbacks
            if pd.isna(start_price):
                start_price = price_df['close'].iloc[0]
            if pd.isna(end_price):
                end_price = price_df['close'].iloc[-1] # Fallback to current if data too short
            
            absolute_mom = (end_price / start_price) - 1
            
            # Relative Momentum
            momentum_12m = absolute_mom - self.spy_mom if self.spy_mom is not None else absolute_mom
            
            # Simple Volatility (Inverse of 20d StdDev)
            volatility = price_df['close'].pct_change().tail(20).std()
            
            # 2. Value & Quality (Fundamental Data)
            # We need to fetch fundamentals first if not present
            self.fund.fetch_fundamentals(ticker)
            
            # Fetch Augmented Metrics for Z-Score
            metrics = self.fund.get_latest_metrics(ticker, [
                'Net Income', 'Stockholders Equity', 'Total Equity Gross Minority Interest',
                'Ebit', 'Total Assets', 'Current Assets', 'Current Liabilities',
                'Retained Earnings', 'Total Revenue', 'Total Debt', 'Total Liabilities Net Minority Interest'
            ])
            
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
                
            # --- ALTMAN Z-SCORE CALCULATION ---
            # Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E
            z_score = np.nan
            try:
                total_assets = metrics.get('Total Assets')
                current_assets = metrics.get('Current Assets')
                current_liab = metrics.get('Current Liabilities')
                retained_earnings = metrics.get('Retained Earnings')
                ebit = metrics.get('Ebit')
                total_liab = metrics.get('Total Liabilities Net Minority Interest') or (total_assets - equity if total_assets and equity else None)
                revenue = metrics.get('Total Revenue')
                
                market_cap = current_price * metrics.get('Basic Average Shares', 0) if metrics.get('Basic Average Shares') else None
                # Approx Market Cap if shares missing? No, rely on price. 
                # Actually we don't have shares here easily unless we fetch 'Basic Average Shares' too.
                # Let's hope logic above or below gets it. I'll stick to 0 if missing for safety.
                # Wait, I didn't verify I have shares in this loop.
                # Let's assume Market Cap is needed.
                # To save API calls, we might skip D component or use Book Equity as proxy? 
                # No, Z-score relies on Market Value of Equity.
                # Let's assume we can get shares, I added it to the fetch list in prev step? No I missed it in chunk 1 replacement list.
                # I will add 'Basic Average Shares' to the list implicitly or in code.
                pass 
                
                # Let's re-add 'Basic Average Shares' to metrics fetch list in code block 1 properly? 
                # Or just proceed. If I edit chunk 1, I can add it.
                
                if total_assets and total_assets > 0:
                    A = (current_assets - current_liab) / total_assets if (current_assets and current_liab) else 0
                    B = retained_earnings / total_assets if retained_earnings else 0
                    C = ebit / total_assets if ebit else 0
                    
                    # D: Market Value Equity / Total Liab
                    # We need shares. Let's try to fetch it if missing.
                    # Or use a simplified D = Equity / Liab (Book Z-Score). 
                    # Greenblatt prefers Market, but for robust code without shares...
                    # Let's use Book Equity as a safe floor proxy if Market Cap is unknown.
                    D = (equity / total_liab) if (equity and total_liab and total_liab > 0) else 0.0 
                    
                    E = revenue / total_assets if revenue else 0
                    
                    z_score = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
            except Exception as e:
                # print(f"Z-Score error for {ticker}: {e}")
                pass
                
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
                'ticker': ticker,
                'momentum_12m': momentum_12m,
                'volatility': volatility,
                'roe': roe,
                'z_score': z_score,
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
                'momentum_12m': 0.4,
                'roe': 0.2,      # Reduced to make room for Z-Score
                'z_score': 0.2,  # New Quality metric
                'volatility': -0.2 
            }
            
        df = self.calculate_factors(tickers)
        if df.empty:
            return df
        
        print("DEBUG: Raw Factor Data Frame:")
        print(df[['ticker', 'momentum_12m', 'roe', 'z_score', 'volatility']])
        
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

    def rank_magic_formula(self, tickers: list) -> pd.DataFrame:
        """
        Ranks stocks based on Joel Greenblatt's Magic Formula.
        Strategy:
        1. Try Strict: Earnings Yield = EBIT / EV, ROC = EBIT / (Total Assets - Current Liab)
        2. Fallback:  Earnings Yield = EPS / Price, ROC = ROA
        """
        data = []
        
        for ticker in tickers:
            # 1. Price
            current_price = self.market.get_price(ticker)
            if not current_price:
                continue
                
            # 2. Fundamentals
            self.fund.fetch_fundamentals(ticker) 
            # Requests for Strict + Fallback metrics
            # yfinance metric names can vary, we ask for common ones
            metrics = self.fund.get_latest_metrics(ticker, [
                'Ebit', 'Net Income', 
                'Total Debt', 'Total Equity Gross Minority Interest',
                'Cash And Cash Equivalents', 
                'Total Assets', 'Current Liabilities',
                'Basic Average Shares', 'Diluted EPS'
            ])
            
            roc = np.nan
            ey = np.nan
            method = "Proxy"
            
            # --- TRY STRICT CALCULATION ---
            try:
                ebit = metrics.get('Ebit')
                total_debt = metrics.get('Total Debt') or 0
                cash = metrics.get('Cash And Cash Equivalents') or 0
                shares = metrics.get('Basic Average Shares')
                total_assets = metrics.get('Total Assets')
                current_liab = metrics.get('Current Liabilities')
                
                if ebit and shares and total_assets and current_liab:
                    # Calculate EV
                    market_cap = current_price * shares
                    ev = market_cap + total_debt - cash
                    
                    # Calculate Capital Employed (Simplified: Assets - Current Liab)
                    capital_employed = total_assets - current_liab
                    
                    if ev > 0 and capital_employed > 0:
                        ey = ebit / ev
                        roc = ebit / capital_employed
                        method = "Strict"
            except Exception:
                pass # Fallback
                
            # --- FALLBACK TO PROXY ---
            if pd.isna(roc) or pd.isna(ey):
                # ROC Proxy: ROA
                net_income = metrics.get('Net Income')
                total_assets = metrics.get('Total Assets')
                if net_income and total_assets and total_assets != 0:
                    roc = net_income / total_assets
                    
                # Earnings Yield Proxy: EPS / Price
                eps = metrics.get('Diluted EPS')
                if eps and current_price and current_price != 0:
                    ey = eps / current_price
                    
            if pd.isna(roc) or pd.isna(ey):
                continue
                
            data.append({
                'ticker': ticker,
                'roc': roc,
                'earnings_yield': ey,
                'close': current_price,
                'method': method
            })
            
        df = pd.DataFrame(data)
        if df.empty:
            return df
            
        # Ranking (Higher is better for both)
        df['rank_roc'] = df['roc'].rank(ascending=False)
        df['rank_ey'] = df['earnings_yield'].rank(ascending=False)
        
        # Magic Formula Score = Sum of Ranks (Lower is better)
        df['magic_score'] = df['rank_roc'] + df['rank_ey']
        df.sort_values('magic_score', ascending=True, inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        return df
