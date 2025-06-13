# backend_app.py
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import requests
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import os
import time
import yfinance as yf # NEW: Import yfinance

app = FastAPI()

# --- Load API Keys from Environment Variables ---
# yfinance does not require an API key as it scrapes Yahoo Finance
# NEWS_API_KEY is still needed for news
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

if not NEWS_API_KEY:
    print("CRITICAL: NEWS_API_KEY environment variable not set. News fetching will NOT work.")

# --- Data Models for Requests ---
class StockDataRequest(BaseModel):
    symbol: str
    timeframe: str = "1y"
    exchange: str = "NSE" # Defaulting to NSE, but can be 'BSE'

class NewsRequest(BaseModel):
    query: str

# --- NLP and Action Mapping Functions (Conceptual/Simple) ---
def perform_ner(text, current_stock_symbol):
    text_lower = text.lower()
    # Updated NER to include common variations for the sample stocks
    if current_stock_symbol.lower() in text_lower or \
       "indian railways catering" in text_lower or \
       "state bank of india" in text_lower or \
       "tata motors" in text_lower or \
       "bharat electronics" in text_lower or \
       "indigo airlines" in text_lower or \
       "bel" in text_lower or \
       "sbi" in text_lower: # Added sbi
        return current_stock_symbol
    return "N/A"

def analyze_sentiment(text):
    positive_keywords = ["profit", "soar", "jump", "rises", "invest", "contract", "boosts", "growth", "strong", "improves", "expands", "dividend", "bullish", "exceeding expectations", "robust", "healthy", "gains", "partnership", "collaboration", "launch"]
    negative_keywords = ["loss", "headwinds", "rising fuel", "supply chain issues", "missed", "resigned", "downgrade", "decline", "fall", "struggle", "uncertainty", "volatility", "challenges"]
    neutral_keywords = ["board approves", "plans", "announces", "decision", "discussions", "talks", "quarterly results"]

    score = 0
    text_lower = text.lower()
    
    for keyword in positive_keywords:
        if keyword in text_lower:
            score += 1
    for keyword in negative_keywords:
        if keyword in text_lower:
            score -= 1

    if score > 0:
        return "positive"
    elif score < 0:
        return "negative"
    else:
        if any(keyword in text_lower for keyword in neutral_keywords):
            return "neutral"
        return "neutral"

def map_news_to_action(sentiment):
    action = "HOLD"
    confidence = round(0.4 + np.random.rand() * 0.2, 2)
    stop_loss = round(np.random.uniform(1.0, 2.0), 2)
    take_profit = round(np.random.uniform(2.0, 4.0), 2)

    if sentiment == "positive":
        action = "BUY"
        confidence = round(0.7 + np.random.rand() * 0.2, 2)
        stop_loss = round(2.5 + np.random.rand() * 1.0, 2)
        take_profit = round(5.0 + np.random.rand() * 2.0, 2)
    elif sentiment == "negative":
        action = "SELL/SHORT"
        confidence = round(0.7 + np.random.rand() * 0.2, 2)
        stop_loss = round(3.0 + np.random.rand() * 1.0, 2)
        take_profit = round(6.0 + np.random.rand() * 2.0, 2)

    return {
        "recommended_action": action,
        "confidence": confidence,
        "stop_loss": stop_loss,
        "take_profit": take_profit
    }

# --- Mock Data Generation (Re-added for fallback) ---
def generate_mock_stock_data_local(timeframe, num_points_override=None):
    """Generates mock OHLCV stock data locally if API fails."""
    data = []
    last_close = np.random.uniform(980, 1020) # Random starting price
    interval_seconds = 0
    num_points = 0

    if timeframe == '5m':
        interval_seconds = 5 * 60
        num_points = 60 # 5 min intervals for 5 hours
    elif timeframe == '1d':
        interval_seconds = 60 * 60 # Hourly data
        num_points = 8 # 8 trading hours in a day
    elif timeframe == '1w':
        interval_seconds = 24 * 60 * 60 # Daily data
        num_points = 5 # 5 trading days
    elif timeframe == '1m':
        interval_seconds = 24 * 60 * 60 # Daily data
        num_points = 20 # ~20 trading days
    elif timeframe == '1y':
        interval_seconds = 24 * 60 * 60 # Daily data
        num_points = 250 # ~250 trading days

    if num_points_override: # Allow overriding num_points for specific needs (e.g., live price)
        num_points = num_points_override

    current_date = datetime.now()
    start_date = current_date - timedelta(seconds=(num_points - 1) * interval_seconds)

    for i in range(num_points):
        open_price = last_close * (1 + (np.random.rand() - 0.5) * 0.02)
        close_price = open_price * (1 + (np.random.rand() - 0.5) * 0.02)
        high_price = max(open_price, close_price) * (1 + np.random.rand() * 0.01)
        low_price = min(open_price, close_price) * (1 - np.random.rand() * 0.01)

        data.append({
            'Date': start_date + timedelta(seconds=i * interval_seconds),
            'Open': round(open_price, 2),
            'High': round(high_price, 2),
            'Low': round(low_price, 2),
            'Close': round(close_price, 2),
            'Volume': int(np.random.randint(100000, 5000000))
        })
        last_close = close_price
    
    return pd.DataFrame(data)

# --- Financial Data Integration (yfinance) ---
# yfinance symbols for Indian stocks typically end with ".NS" for NSE and ".BO" for BSE
# Example: IRCTC.NS for NSE, RELIANCE.BO for BSE

def get_yfinance_symbol(symbol: str, exchange: str = "NSE"):
    """Constructs the yfinance symbol based on exchange."""
    if exchange.upper() == "NSE":
        return f"{symbol}.NS"
    elif exchange.upper() == "BSE":
        return f"{symbol}.BO"
    return symbol # Fallback if no specific exchange

def get_live_stock_price_yf(symbol: str, exchange: str = "NSE"):
    """Attempts to fetch live stock price from yfinance, falls back to mock."""
    yf_symbol = get_yfinance_symbol(symbol, exchange)
    print(f"Attempting yfinance live price for: {yf_symbol}")
    try:
        ticker = yf.Ticker(yf_symbol)
        # Fetch current price (can be 'currentPrice', 'regularMarketPrice', or 'ask'/'bid')
        # 'info' dictionary contains a lot of data. 'regularMarketPrice' is usually good.
        live_price = ticker.info.get('regularMarketPrice') 
        
        if live_price is not None:
            print(f"yfinance: Successfully fetched live price for {yf_symbol}: {live_price}")
            return float(live_price)
        else:
            print(f"yfinance: No live price found for {yf_symbol} in ticker info. Generating mock.")
            return generate_mock_stock_data_local(timeframe='5m', num_points_override=1)['Close'].iloc[-1]
    except Exception as e:
        print(f"Fallback: yfinance live price failed for {yf_symbol}: {e}. Generating mock.")
        return generate_mock_stock_data_local(timeframe='5m', num_points_override=1)['Close'].iloc[-1]

def get_historical_ohlc_yf(symbol: str, timeframe: str, exchange: str = "NSE"):
    """Attempts to fetch historical OHLC data from yfinance, falls back to mock."""
    yf_symbol = get_yfinance_symbol(symbol, exchange)
    print(f"Attempting yfinance historical data for: {yf_symbol} ({timeframe})")

    period_map = {
        '5m': '1d', # yfinance 'interval' for 5m needs 'period' like '1d' or '5d'
        '1d': '5d', # yfinance 'interval' for 1h/60m needs 'period' like '5d'
        '1w': '1mo', # yfinance 'interval' for 1d needs 'period' like '1mo'
        '1m': '3mo',
        '1y': '1y'
    }
    interval_map = {
        '5m': '5m',
        '1d': '60m', # Hourly interval for 1 day
        '1w': '1d', # Daily interval for 1 week
        '1m': '1d', # Daily interval for 1 month
        '1y': '1d'  # Daily interval for 1 year
    }

    period = period_map.get(timeframe, '1y') # Default period
    interval = interval_map.get(timeframe, '1d') # Default interval

    try:
        ticker = yf.Ticker(yf_symbol)
        # Fetch history data
        # 'period' parameter can be '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'
        # 'interval' parameter can be '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo'
        df = ticker.history(period=period, interval=interval)

        if not df.empty:
            df = df.rename(columns={
                "Open": "Open", "High": "High", "Low": "Low",
                "Close": "Close", "Volume": "Volume"
            })
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            df.index.name = 'Date' # Ensure index is named Date
            print(f"yfinance: Successfully fetched {len(df)} historical points for {yf_symbol} ({timeframe}).")
            return df
        else:
            print(f"yfinance: No historical data found for {yf_symbol} ({timeframe}). Generating mock.")
            return generate_mock_stock_data_local(timeframe=timeframe)
    except Exception as e:
        print(f"Fallback: yfinance historical data failed for {yf_symbol} ({timeframe}): {e}. Generating mock.")
        return generate_mock_stock_data_local(timeframe=timeframe)

# --- News API Integration (NewsAPI.org) ---
def get_financial_news_api(query: str, language: str = 'en', sort_by: str = 'relevancy', days_back: int = 30):
    """Fetches news articles from NewsAPI.org."""
    if not NEWS_API_KEY:
        print("Fallback: NEWS_API_KEY not set. Returning mock news.")
        return [{
            "source": "Mock News", "title": f"Mock News for {query} - Key Missing",
            "content": "This is a mock news article because the NewsAPI key is not configured or an error occurred.",
            "url": "#", "publishedAt": datetime.now().isoformat(), "event": "Mock Event"
        }]

    from_date = (datetime.now() - timedelta(days=days_back)).isoformat()

    params = {
        "q": query,
        "language": language,
        "sortBy": sort_by,
        "from": from_date,
        "apiKey": NEWS_API_KEY,
        "pageSize": 20
    }
    
    print(f"Attempting NewsAPI.org for query: '{query}'")
    try:
        response = requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data["status"] == "ok":
            articles = []
            for article in data["articles"]:
                articles.append({
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "title": article.get("title", "No Title"),
                    "content": article.get("description", article.get("content", "No content available")),
                    "url": article.get("url", "#"),
                    "publishedAt": article.get("publishedAt", "N/A"),
                    "event": "General News"
                })
            print(f"NewsAPI.org: Successfully fetched {len(articles)} news articles for '{query}'.")
            return articles
        elif data["status"] == "error":
            error_msg = data['message']
            print(f"NewsAPI.org Error for '{query}': {error_msg}")
            if "maximum results for free plan" in error_msg:
                print(f"Fallback: NewsAPI.org free plan limit. Returning mock news.")
                return [{
                    "source": "Mock News", "title": f"Mock News for {query} - Rate Limit",
                    "content": "This is a mock news article due to NewsAPI.org rate limits.",
                    "url": "#", "publishedAt": datetime.now().isoformat(), "event": "Mock Event"
                }]
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"NewsAPI.org API error: {error_msg}")
    except requests.exceptions.Timeout:
        print(f"Fallback: NewsAPI.org Timeout for '{query}'. Returning mock news.")
        return [{
            "source": "Mock News", "title": f"Mock News for {query} - Timeout",
            "content": "This is a mock news article due to NewsAPI.org timeout.",
            "url": "#", "publishedAt": datetime.now().isoformat(), "event": "Mock Event"
        }]
    except requests.exceptions.RequestException as e:
        print(f"Fallback: NewsAPI.org Request failed for '{query}': {e}. Returning mock news.")
        return [{
            "source": "Mock News", "title": f"Mock News for {query} - Request Failed",
            "content": "This is a mock news article due to NewsAPI.org request failure.",
            "url": "#", "publishedAt": datetime.now().isoformat(), "event": "Mock Event"
        }]

# --- FastAPI Endpoints ---

@app.get("/")
async def read_root():
    return {"message": "Stock News Bot Backend API is running! Access specific endpoints for data."}

@app.get("/live_price/{symbol}")
async def get_live_price_endpoint(symbol: str, exchange: str = "NSE"):
    print(f"Backend received request for live price: {symbol} ({exchange})")
    try:
        # Call the yfinance function here
        price = get_live_stock_price_yf(symbol, exchange)
        return {"symbol": symbol, "price": price}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unhandled error in /live_price: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

@app.post("/historical_data")
async def get_historical_data_endpoint(request: StockDataRequest):
    print(f"Backend received request for historical data: {request.symbol} ({request.timeframe}, {request.exchange})")
    try:
        # Call the yfinance function here
        df = get_historical_ohlc_yf(request.symbol, request.timeframe, request.exchange)
        
        if df.empty:
            # If yfinance fallback to mock also results in empty, raise 404
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No data available for {request.symbol} for {request.timeframe} after fallback.")
        
        # Ensure 'Date' index is converted to a string column for JSON serialization
        # df.index is already named 'Date' from yfinance, so reset_index() will make 'Date' a column
        df_reset = df.reset_index()
        # Convert datetime objects in 'Date' column to ISO format string
        df_reset['Date'] = df_reset['Date'].dt.strftime('%Y-%m-%dT%H:%M:%S')
        
        return df_reset.to_dict(orient='records')
    except HTTPException as e:
        raise e
    except Exception as e:
        # Catch any other unexpected errors during DataFrame processing or return
        print(f"Unhandled error in /historical_data: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

@app.post("/news_analysis")
async def get_news_and_analysis_endpoint(request: NewsRequest):
    print(f"Backend received request for news analysis: {request.query}")
    try:
        raw_articles = get_financial_news_api(f"{request.query} stock")

        processed_news = []
        latest_trading_signal = {
            "ticker": request.query,
            "sentiment": "N/A",
            "event": "N/A",
            "confidence": 0.00,
            "recommended_action": "HOLD",
            "stop_loss": 0.00,
            "take_profit": 0.00
        }

        if not raw_articles:
            return {"news": [], "trading_signal": latest_trading_signal}

        for i, news_item in enumerate(raw_articles):
            full_text = f"{news_item.get('title', '')} {news_item.get('content', '')}"
            
            ticker_identified = perform_ner(full_text, request.query)
            sentiment = analyze_sentiment(full_text)
            action_data = map_news_to_action(sentiment)

            processed_news_item = {
                "source": news_item["source"],
                "title": news_item["title"],
                "content": news_item["content"],
                "url": news_item["url"],
                "publishedAt": news_item["publishedAt"],
                "sentiment": sentiment,
                "event": news_item["event"],
                "recommended_action": action_data["recommended_action"],
                "confidence": action_data["confidence"]
            }
            processed_news.append(processed_news_item)

            if i == 0:
                latest_trading_signal = {
                    "ticker": ticker_identified,
                    "sentiment": sentiment,
                    "event": news_item["event"],
                    "confidence": action_data["confidence"],
                    "recommended_action": action_data["recommended_action"],
                    "stop_loss": action_data["stop_loss"],
                    "take_profit": action_data["take_profit"]
                }
        
        return {"news": processed_news, "trading_signal": latest_trading_signal}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unhandled error in /news_analysis: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")
