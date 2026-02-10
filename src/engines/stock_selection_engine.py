import pandas as pd
import numpy as np
from src.data.market_data import MarketDataFetcher
from src.data.fundamental_data import FundamentalDataFetcher
from src.data.store import DataStore
from src.engines.ta_overlay import TechnicalAnalysis
from sklearn.preprocessing import StandardScaler

class StockSelectionEngine:
    def __init__(self):
        self.market = MarketDataFetcher()
        self.fund = FundamentalDataFetcher()
        self.store = DataStore()

    def calculate_factors(self, tickers: list) -> pd.DataFrame:
        """
        Calculates Value, Quality, and Momentum factors for a list of tickers utilizing LOCAL DB only.
        Returns a DataFrame with raw factor values.
        """
        data = []
        
        # 0. Fetch Benchmark (SPY) for Relative Momentum from DB
        self.spy_mom = 0.0
        try:
            # Direct DB Fetch
            spy_df = self.store.get_market_data("SPY")
            if not spy_df.empty and len(spy_df) > 250:
                 # SPY 12-1 Month Calculation
                 spy_start = spy_df['close'].asfreq('B').shift(252).iloc[-1]
                 spy_end = spy_df['close'].asfreq('B').shift(21).iloc[-1] # 1 month ago
                 
                 if not pd.isna(spy_start) and not pd.isna(spy_end):
                     self.spy_mom = (spy_end / spy_start) - 1
                     # print(f"Benchmark SPY 12-1m Return: {self.spy_mom:.2%}")
        except Exception as e:
            print(f"Error fetching SPY benchmark: {e}")

        # 1. Batch Fetch Fundamentals & Info (HUGE SPEEDUP)
        print("Batch fetching fundamentals from DB...")
        fund_metrics_list = [
            'Net Income', 'Stockholders Equity', 'Total Equity Gross Minority Interest',
            'Ebit', 'Total Assets', 'Current Assets', 'Current Liabilities',
            'Retained Earnings', 'Total Revenue', 'Total Debt', 
            'Total Liabilities Net Minority Interest', 'Basic Average Shares'
        ]
        batch_fundamentals = self.store.get_latest_fundamentals(tickers, fund_metrics_list)
        # batch_info = self.store.get_latest_stock_info(tickers) # Not used heavily in Z-Score but good for Fallbacks? keeping it simplified.

        # 2. Loop Tickers
        for ticker in tickers:
            # print(f"Processing {ticker}...")
            # Momentum (Market Data from DB)
            price_df = self.store.get_market_data(ticker)
            if price_df.empty:
                continue
            
            # Current Price
            current_price = price_df['close'].iloc[-1]
            
            # 12-1 Month Momentum
            # Window: From 12 months ago to 1 month ago.
            start_price = price_df['close'].asfreq('B').shift(252).iloc[-1]
            end_price = price_df['close'].asfreq('B').shift(21).iloc[-1]
            
            # Fallbacks
            if pd.isna(start_price):
                start_price = price_df['close'].iloc[0]
            if pd.isna(end_price):
                end_price = price_df['close'].iloc[-1]
            
            absolute_mom = (end_price / start_price) - 1
            
            # Relative Momentum
            momentum_12m = absolute_mom - self.spy_mom if self.spy_mom is not None else absolute_mom
            
            # Volatility
            volatility = price_df['close'].pct_change().tail(20).std()
            
            # Fundamentals from Batch
            metrics = batch_fundamentals.get(ticker, {})
            
            net_income = metrics.get('Net Income')
            equity = metrics.get('Stockholders Equity') or metrics.get('Total Equity Gross Minority Interest')
            
            roe = np.nan
            if net_income and equity and equity != 0:
                roe = net_income / equity
                
            # --- ALTMAN Z-SCORE CALCULATION ---
            z_score = np.nan
            try:
                total_assets = metrics.get('Total Assets')
                current_assets = metrics.get('Current Assets')
                current_liab = metrics.get('Current Liabilities')
                retained_earnings = metrics.get('Retained Earnings')
                ebit = metrics.get('Ebit')
                total_liab = metrics.get('Total Liabilities Net Minority Interest') or (total_assets - equity if total_assets and equity else None)
                revenue = metrics.get('Total Revenue')
                
                if total_assets and total_assets > 0:
                    A = (current_assets - current_liab) / total_assets if (current_assets and current_liab) else 0
                    B = retained_earnings / total_assets if retained_earnings else 0
                    C = ebit / total_assets if ebit else 0
                    
                    # D: Market Value Equity / Total Liab
                    # Use Book Equity as safe proxy if no shares data, or if shares data exists, use Market Cap
                    shares = metrics.get('Basic Average Shares')
                    if shares:
                        market_cap = current_price * shares
                        D = market_cap / total_liab if (total_liab and total_liab > 0) else 0.0
                    else:
                        # Fallback to Book Equity
                        D = (equity / total_liab) if (equity and total_liab and total_liab > 0) else 0.0 
                    
                    E = revenue / total_assets if revenue else 0
                    
                    z_score = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
            except Exception:
                pass
            
            data.append({
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
            weights = {
                'momentum_12m': 0.4,
                'roe': 0.2,
                'z_score': 0.2,
                'volatility': -0.2 
            }
            
        df = self.calculate_factors(tickers)
        if df.empty:
            return df
        
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
        # Use local DB strictly
        ta_signals = []
        for index, row in df.iterrows():
            if index >= 20: # Optimization: Only TA check top 20
                ta_signals.append({'trend_status': 'N/A', 'ta_action': 'Hold'})
                continue

            price_df = self.store.get_market_data(row['ticker'])
            if len(price_df) < 50:
                 ta_signals.append({'trend_status': 'Insuff. Data', 'ta_action': 'Wait'})
                 continue

            price_df = TechnicalAnalysis.add_indicators(price_df)
            setup = TechnicalAnalysis.check_trend_setup(price_df)
            
            ta_signals.append({
                'trend_status': setup['trend'],
                'ta_action': setup['ta_signal']
            })
            
        ta_df = pd.DataFrame(ta_signals)
        df = pd.concat([df, ta_df], axis=1)
        
        # --- RANK CHANGE TRACKING ---
        prev_ranks = self.store.get_previous_rankings("smart_beta")
        changes = []
        for rank, row in df.iterrows():
            current_rank = rank + 1
            ticker = row['ticker']
            if ticker in prev_ranks:
                prev_rank = prev_ranks[ticker]
                change = prev_rank - current_rank # Positive means improved (e.g. 5 -> 2 = +3)
            else:
                change = None # New entry
            changes.append(change)
            
        df['rank_change'] = changes
        
        # Save History
        self.store.save_ranking_history("smart_beta", df)
        
        return df

    def rank_magic_formula(self, tickers: list) -> pd.DataFrame:
        """
        Ranks stocks based on Joel Greenblatt's Magic Formula using LOCAL DB.
        """
        data = []
        
        # Batch Fetch
        mf_metrics = [
            'Ebit', 'Net Income', 'Total Debt', 'Total Equity Gross Minority Interest',
            'Cash And Cash Equivalents', 'Total Assets', 'Current Liabilities',
            'Basic Average Shares', 'Diluted EPS'
        ]
        batch_fundamentals = self.store.get_latest_fundamentals(tickers, mf_metrics)

        for ticker in tickers:
            # 1. Price
            price_df = self.store.get_market_data(ticker)
            if price_df.empty:
                continue
            current_price = price_df['close'].iloc[-1]
                
            # 2. Fundamentals
            metrics = batch_fundamentals.get(ticker, {})
            
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
                    market_cap = current_price * shares
                    ev = market_cap + total_debt - cash
                    capital_employed = total_assets - current_liab
                    
                    if ev > 0 and capital_employed > 0:
                        ey = ebit / ev
                        roc = ebit / capital_employed
                        method = "Strict"
            except Exception:
                pass
                
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
            
        # Ranking
        df['rank_roc'] = df['roc'].rank(ascending=False)
        df['rank_ey'] = df['earnings_yield'].rank(ascending=False)
        df['magic_score'] = df['rank_roc'] + df['rank_ey']
        df.sort_values('magic_score', ascending=True, inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        # --- RANK CHANGE TRACKING ---
        prev_ranks = self.store.get_previous_rankings("magic_formula")
        changes = []
        for rank, row in df.iterrows():
            current_rank = rank + 1
            ticker = row['ticker']
            if ticker in prev_ranks:
                prev_rank = prev_ranks[ticker]
                change = prev_rank - current_rank
            else:
                change = None
            changes.append(change)
            
        df['rank_change'] = changes
        
        # Save History
        self.store.save_ranking_history("magic_formula", df)
        
        return df

    def rank_garp(self, tickers: list) -> pd.DataFrame:
        """
        Ranks stocks based on GARP (Growth at Reasonable Price) using LOCAL DB.
        Criteria:
        1. PEG < 2.0 (Lower is better)
        2. Revenue Growth > 15% (Higher is better)
        """
        data = []
        
        # 1. Batch Fetch Reference Data (PEG, Growth)
        batch_info = self.store.get_latest_stock_info(tickers)
        
        # 2. Batch Fetch Fundamentals (ROE)
        # We want ROE as a quality check
        batch_fundamentals = self.store.get_latest_fundamentals(tickers, ['Net Income', 'Stockholders Equity'])
        
        for ticker in tickers:
            # Price
            price_df = self.store.get_market_data(ticker)
            if price_df.empty:
                continue
            current_price = price_df['close'].iloc[-1]
            
            # Info
            info = batch_info.get(ticker, {})
            peg = info.get('peg_ratio')
            growth = info.get('revenue_growth')
            
            # Fundamentals
            fund = batch_fundamentals.get(ticker, {})
            net_income = fund.get('Net Income')
            equity = fund.get('Stockholders Equity')
            
            roe = np.nan
            if net_income and equity and equity != 0:
                roe = net_income / equity
                
            # Filter Logic (Optional: or just score everything)
            # Let's include everything that has valid PEG/Growth
            if pd.isna(peg) or pd.isna(growth):
                continue
                
            data.append({
                'ticker': ticker,
                'peg': peg,
                'growth': growth,
                'roe': roe,
                'close': current_price
            })
            
        df = pd.DataFrame(data)
        if df.empty:
            return df
            
        # Ranking
        # PEG: Lower is better. Rank Ascending.
        df['rank_peg'] = df['peg'].rank(ascending=True)
        
        # Growth: Higher is better. Rank Descending.
        df['rank_growth'] = df['growth'].rank(ascending=False)
        
        # Composite GARP Score (Lower is better sum of ranks)
        df['garp_score'] = df['rank_peg'] + df['rank_growth'] 
        
        df.sort_values('garp_score', ascending=True, inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        return df
