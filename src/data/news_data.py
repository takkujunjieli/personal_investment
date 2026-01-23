import yfinance as yf
import pandas as pd
from datetime import datetime

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    SentimentIntensityAnalyzer = None

class NewsDataFetcher:
    def __init__(self):
        if SentimentIntensityAnalyzer:
            self.analyzer = SentimentIntensityAnalyzer()
        else:
            self.analyzer = None
            print("Warning: vaderSentiment not found. Sentiment analysis will be disabled.")

    def fetch_news_sentiment(self, ticker: str) -> pd.DataFrame:
        """
        Fetches latest news from yfinance and computes sentiment scores.
        """
        stock = yf.Ticker(ticker)
        news = stock.news
        
        records = []
        for item in news:
            title = item.get('title', '')
            link = item.get('link', '')
            pub_time = item.get('providerPublishTime', 0)
            
            # Simple conversion of timestamp
            pub_date = datetime.fromtimestamp(pub_time).strftime('%Y-%m-%d %H:%M:%S')
            
            score = 0
            if self.analyzer:
                sentiment = self.analyzer.polarity_scores(title)
                score = sentiment['compound']
            
            records.append({
                'date': pub_date,
                'title': title,
                'sentiment': score,
                'link': link
            })
            
        df = pd.DataFrame(records)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df.sort_values('date', ascending=False, inplace=True)
        
        return df

    def get_aggregated_sentiment(self, ticker: str) -> float:
        """
        Returns average sentiment of recent news (-1 to 1).
        """
        df = self.fetch_news_sentiment(ticker)
        if df.empty:
            return 0.0
        return df['sentiment'].mean()
