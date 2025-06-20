# pages/SBI.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import yfinance as yf # Import yfinance directly
import os # To access environment variables if st.secrets not used (for local testing mostly)
import pytz # NEW: Import pytz for timezone handling
import pandas_ta as ta # NEW: Import pandas_ta for technical indicators

# --- NEW: Import streamlit_autorefresh for live updates ---
from streamlit_autorefresh import st_autorefresh

# --- Stock-Specific Configuration ---
CURRENT_STOCK = "SBI"

# --- API Key Configuration (for Streamlit Cloud: use st.secrets) ---
NEWS_API_KEY = st.secrets.get("NEWS_API_KEY")

if not NEWS_API_KEY:
    st.warning("NewsAPI.org API Key not found. News data will be mocked. "
                "Please add it to your Streamlit secrets or environment variables.")

# --- NLP and Action Mapping Functions (Directly in Streamlit app) ---
def perform_ner(text, current_stock_symbol):
    """
    Performs Named Entity Recognition to identify stock symbols and high-impact events in text.
    It checks for aliases of the current stock and other predefined stocks.
    Also identifies specific financial events.
    """
    text_lower = text.lower()
    identified_ticker = "N/A"
    identified_event = "General News" # Default event

    # Define common names/aliases for various stocks
    stock_aliases = {
        "IRCTC": ["irctc", "indian railways catering", "railways"],
        "SBI": ["sbi", "state bank of india", "state bank", "s.b.i."], # Added "state bank"
        "TATA MOTORS": ["tata motors", "tata"],
        "BHARAT ELECTRONICS": ["bharat electronics", "bel"],
        "INDIGO AIRLINES": ["indigo airlines", "indigo", "interglobe aviation"]
    }
    
    # Define high-impact financial keywords/phrases
    high_impact_events = {
        "CEO Resignation": ["ceo resigns", "ceo stepping down", "chief executive officer resigns"],
        "Earnings Drop": ["earnings drop", "profit decline", "revenue miss", "lower than expected results", "loss reported"],
        "Earnings Beat": ["earnings beat", "profit rise", "revenue beat", "exceeds expectations", "strong results"],
        "Acquisition/Merger": ["acquisition", "merger", "takes over", "acquires", "buys out"],
        "Regulatory Fine/Scandal": ["regulatory fine", "investigation", "scandal", "fraud", "penalty", "sanctions"],
        "Product Launch/Approval": ["product launch", "new product", "approval received", "fda approval", "drug approved", "new service"],
        "Dividend Announcement": ["dividend announced", "interim dividend", "final dividend", "special dividend"],
        "Partnership/Collaboration": ["partnership", "collaboration", "joint venture", "agreement signed"],
        "Credit Rating Change": ["credit rating downgrade", "credit rating upgrade", "rating cut", "rating outlook"],
        "NPA/Asset Quality": ["npa increase", "bad loans", "asset quality worsens", "npa reduction", "asset quality improves"] # Banking specific
    }

    # Prioritize checking for aliases of the current stock symbol
    current_stock_upper = current_stock_symbol.upper()
    if current_stock_upper in stock_aliases:
        for alias in stock_aliases[current_stock_upper]:
            if alias in text_lower:
                identified_ticker = current_stock_symbol # Return the current stock if its alias is found
                break # Found the current stock, no need to check other aliases for it
    
    # If the current stock's alias isn't found, check for other stock symbols
    if identified_ticker == "N/A":
        for stock_sym, aliases in stock_aliases.items():
            if stock_sym.upper() != current_stock_upper: # Avoid re-checking the current stock
                for alias in aliases:
                    if alias in text_lower:
                        identified_ticker = stock_sym # Return the identified stock symbol
                        break # Found another stock, stop checking aliases
            if identified_ticker != "N/A":
                break # Found a stock, stop checking other stock symbols

    # Check for high-impact events
    for event, keywords in high_impact_events.items():
        if any(keyword in text_lower for keyword in keywords):
            identified_event = event
            break # Found an event, no need to check further

    return identified_ticker, identified_event # Return both ticker and event

def analyze_sentiment(text):
    """
    Analyzes the sentiment of the given text based on predefined keywords.
    Categorizes sentiment as 'positive', 'negative', or 'neutral'.
    Includes banking-specific keywords for better accuracy for SBI.
    """
    positive_keywords = ["profit", "soar", "jump", "rises", "invest", "contract", "boosts", "growth", "strong", "improves", "expands", "dividend", "bullish", "exceeding expectations", "robust", "healthy", "gains", "partnership", "collaboration", "launch", "loan growth", "deposit growth", "asset quality improves", "NPA reduction", "credit expansion", "record", "increase", "up", "breakthrough", "acquires", "merger", "agreement"]
    negative_keywords = ["loss", "headwinds", "rising fuel", "supply chain issues", "missed", "resigned", "downgrade", "decline", "fall", "struggle", "uncertainty", "volatility", "challenges", "NPA increase", "fraud", "scam", "regulatory fine", "warning", "decrease", "down", "crisis", "investigation", "penalty"]
    neutral_keywords = ["board approves", "plans", "announces", "decision", "discussions", "talks", "quarterly results", "RBI", "policy", "interest rates", "reports", "outlook", "meeting"]

    score = 0
    text_lower = text.lower()
    
    # Count occurrences of positive and negative keywords
    for keyword in positive_keywords:
        if keyword in text_lower:
            score += 1
    for keyword in negative_keywords:
        if keyword in text_lower:
            score -= 1

    # Determine sentiment based on score
    if score > 0:
        return "positive"
    elif score < 0:
        return "negative"
    else:
        # If score is zero, check for neutral keywords
        if any(keyword in text_lower for keyword in neutral_keywords):
            return "neutral"
        return "neutral" # Default to neutral if no specific keywords found

def map_news_to_action(sentiment, event, current_price=None):
    """
    Maps sentiment analysis results and identified events to a recommended trading action.
    Generates simulated confidence, stop-loss, and take-profit values.
    High-impact events can override general sentiment.
    """
    action = "HOLD"
    confidence = round(0.4 + np.random.rand() * 0.2, 2) # Base confidence for HOLD
    stop_loss_pct = round(np.random.uniform(1.0, 2.0), 2) / 100 # Default 1-2%
    take_profit_pct = round(np.random.uniform(2.0, 4.0), 2) / 100 # Default 2-4%

    # Adjust based on sentiment
    if sentiment == "positive":
        action = "BUY"
        confidence = round(0.7 + np.random.rand() * 0.2, 2) # Higher confidence for BUY
        stop_loss_pct = round(2.5 + np.random.rand() * 1.0, 2) / 100 # 2.5-3.5%
        take_profit_pct = round(5.0 + np.random.rand() * 2.0, 2) / 100 # 5-7%
    elif sentiment == "negative":
        action = "SELL/SHORT"
        confidence = round(0.7 + np.random.rand() * 0.2, 2) # Higher confidence for SELL/SHORT
        stop_loss_pct = round(3.0 + np.random.rand() * 1.0, 2) / 100 # 3-4%
        take_profit_pct = round(6.0 + np.random.rand() * 2.0, 2) / 100 # 6-8%

    # Override/Adjust based on high-impact events
    if event in ["CEO Resignation", "Earnings Drop", "Regulatory Fine/Scandal", "NPA Increase"]:
        action = "STRONG SELL"
        confidence = round(0.85 + np.random.rand() * 0.1, 2) # Very high confidence
        stop_loss_pct = round(4.0 + np.random.rand() * 1.0, 2) / 100 # Tighter stop loss
        take_profit_pct = round(7.0 + np.random.rand() * 3.0, 2) / 100 # Higher take profit
    elif event in ["Earnings Beat", "Acquisition/Merger", "Product Launch/Approval", "Partnership/Collaboration", "Credit Rating Change", "NPA Reduction"]:
        action = "STRONG BUY"
        confidence = round(0.85 + np.random.rand() * 0.1, 2) # Very high confidence
        stop_loss_pct = round(3.0 + np.random.rand() * 1.0, 2) / 100
        take_profit_pct = round(8.0 + np.random.rand() * 3.0, 2) / 100

    stop_loss = None
    take_profit = None
    if current_price:
        stop_loss = round(current_price * (1 - stop_loss_pct), 2) if action == "BUY" or action == "STRONG BUY" else round(current_price * (1 + stop_loss_pct), 2)
        take_profit = round(current_price * (1 + take_profit_pct), 2) if action == "BUY" or action == "STRONG BUY" else round(current_price * (1 - take_profit_pct), 2)
    
    return {
        "recommended_action": action,
        "confidence": confidence,
        "stop_loss": stop_loss,
        "take_profit": take_profit
    }

# --- Mock Data Generation (Fallback if yfinance/NewsAPI fail) ---
def generate_mock_stock_data_local(timeframe, num_points_override=None):
    """
    Generates mock stock OHLCV data for testing or fallback when APIs fail.
    Adjusted initial price range for SBI.
    """
    data = []
    # Adjusted initial price range for SBI (typically lower than IRCTC's current values)
    last_close = np.random.uniform(600, 700) 
    interval_seconds = 0
    num_points = 0

    # Determine interval and number of points based on selected timeframe
    if timeframe == '5m': interval_seconds = 5 * 60; num_points = 60
    elif timeframe == '1d': interval_seconds = 60 * 60; num_points = 8
    elif timeframe == '1w': interval_seconds = 24 * 60 * 60; num_points = 5
    elif timeframe == '1m': interval_seconds = 24 * 60 * 60; num_points = 20
    elif timeframe == '1y': interval_seconds = 24 * 60 * 60; num_points = 250
    
    # Allow overriding number of points for specific scenarios (e.g., live price mock)
    if num_points_override: num_points = num_points_override

    current_date = datetime.now()
    start_date = current_date - timedelta(seconds=(num_points - 1) * interval_seconds)

    # Generate data points
    for i in range(num_points):
        open_price = last_close * (1 + (np.random.rand() - 0.5) * 0.02)
        close_price = open_price * (1 + (np.random.rand() - 0.5) * 0.02)
        high_price = max(open_price, close_price) * (1 + np.random.rand() * 0.01)
        low_price = min(open_price, close_price) * (1 - np.random.rand() * 0.01)
        data.append({
            'Date': start_date + timedelta(seconds=i * interval_seconds),
            'Open': round(open_price, 2), 'High': round(high_price, 2),
            'Low': round(low_price, 2), 'Close': round(close_price, 2),
            'Volume': int(np.random.randint(100000, 5000000))
        })
        last_close = close_price # Update last close for next iteration
    return pd.DataFrame(data)

# --- Financial Data Integration (yfinance) ---
def get_yfinance_symbol(symbol: str, exchange: str = "NSE"):
    """
    Maps a common stock name to its yfinance symbol, including exchange suffixes.
    """
    # Mapping for common stock names to yfinance symbols for Indian stocks
    symbol_map = {
        "IRCTC": "IRCTC.NS",
        "SBI": "SBIN.NS",
        "TATA MOTORS": "TATAMOTORS.NS",
        "BHARAT ELECTRONICS": "BEL.NS",
        "INDIGO AIRLINES": "INDIGO.NS" # InterGlobe Aviation Ltd. is the parent company for Indigo
    }
    
    yf_base_symbol = symbol_map.get(symbol.upper(), symbol) # Use mapped symbol if available, otherwise use original symbol

    # Append exchange suffix if not already present
    if exchange.upper() == "NSE": 
        if not yf_base_symbol.endswith(".NS"):
            return f"{yf_base_symbol}.NS"
        return yf_base_symbol
    elif exchange.upper() == "BSE": 
        if not yf_base_symbol.endswith(".BO"):
            return f"{yf_base_symbol}.BO"
        return yf_base_symbol
    return yf_base_symbol # Fallback: return as is if exchange is not NSE/BSE or no suffix is needed

@st.cache_data(ttl=30) # Cache for 30 seconds to allow frequent updates by st_autorefresh
def get_live_stock_price_yf(symbol: str, exchange: str = "NSE"):
    """
    Fetches the live stock price from yfinance. Includes fallback to historical data
    or mock data if live price is not immediately available.
    """
    yf_symbol = get_yfinance_symbol(symbol, exchange)
    # print(f"Attempting yfinance live price for: {yf_symbol}") # Debugging print
    try:
        ticker = yf.Ticker(yf_symbol)
        live_price = ticker.info.get('regularMarketPrice') 
        
        # Fallback logic if 'regularMarketPrice' is not available
        if live_price is None:
            live_price = ticker.info.get('currentPrice')
        if live_price is None:
            hist_data = ticker.history(period="1d", interval="1m")
            if not hist_data.empty:
                live_price = hist_data['Close'].iloc[-1]

        if live_price is not None:
            # print(f"yfinance: Successfully fetched live price for {yf_symbol}: {live_price}") # Debugging print
            return float(live_price)
        else:
            # print(f"yfinance: No live price found for {yf_symbol} in ticker info. Generating mock.") # Debugging print
            # Fallback to mock data for a single price point
            return generate_mock_stock_data_local(timeframe='5m', num_points_override=1)['Close'].iloc[-1]
    except Exception as e:
        # print(f"Fallback: yfinance live price failed for {yf_symbol}: {e}. Generating mock.") # Debugging print
        # Fallback to mock data on API failure
        return generate_mock_stock_data_local(timeframe='5m', num_points_override=1)['Close'].iloc[-1]

# --- NEW: Technical Indicator Calculation Functions ---
def calculate_technical_indicators(df):
    """
    Calculates various technical indicators using pandas_ta and adds them to the DataFrame.
    """
    if df.empty:
        return df

    # SMA (Simple Moving Average)
    df.ta.sma(length=20, append=True) # SMA_20
    df.ta.sma(length=50, append=True) # SMA_50

    # EMA (Exponential Moving Average)
    df.ta.ema(length=20, append=True) # EMA_20
    df.ta.ema(length=50, append=True) # EMA_50

    # RSI (Relative Strength Index)
    df.ta.rsi(length=14, append=True) # RSI_14

    # MACD (Moving Average Convergence Divergence)
    df.ta.macd(append=True) # MACD, MACDH, MACDS

    # Bollinger Bands
    df.ta.bbands(append=True) # BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0, BBP_20_2.0

    # Clean up column names from pandas_ta if needed (e.g., remove 'Close' prefix if it adds one)
    # pandas_ta usually adds clean names, but it's good to be aware.
    return df

@st.cache_data(ttl=15 * 60) # Cache for 15 minutes for historical data
def get_historical_ohlc_yf(symbol: str, timeframe: str, exchange: str = "NSE"):
    """
    Fetches historical OHLCV data from yfinance based on specified timeframe.
    Calculates technical indicators on the fetched data.
    """
    yf_symbol = get_yfinance_symbol(symbol, exchange)
    # print(f"Attempting yfinance historical data for: {yf_symbol} ({timeframe})") # Debugging print

    # Map desired timeframe to yfinance's period and interval parameters
    period_map = {'5m': '1d', '1d': '5d', '1w': '1mo', '1m': '3mo', '1y': '1y'}
    interval_map = {'5m': '5m', '1d': '60m', '1w': '1d', '1m': '1d', '1y': '1d'}

    period = period_map.get(timeframe, '1y')
    interval = interval_map.get(timeframe, '1d')

    try:
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=period, interval=interval)

        if not df.empty:
            # Rename columns to a consistent format and select relevant ones
            df = df.rename(columns={"Open": "Open", "High": "High", "Low": "Low", "Close": "Close", "Volume": "Volume"})
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            df.index.name = 'Date' # Ensure the index is named 'Date'
            
            # NEW: Calculate technical indicators
            df = calculate_technical_indicators(df.copy()) # Use a copy to avoid modifying original df in cache directly
            
            # print(f"yfinance: Successfully fetched {len(df)} historical points for {yf_symbol} ({timeframe}).") # Debugging print
            return df
        else:
            # print(f"yfinance: No historical data found for {yf_symbol} ({timeframe}). Generating mock.") # Debugging print
            # Fallback to mock data if yfinance returns empty
            mock_df = generate_mock_stock_data_local(timeframe=timeframe)
            mock_df = calculate_technical_indicators(mock_df) # Calculate indicators for mock data too
            return mock_df
    except Exception as e:
        # print(f"Fallback: yfinance historical data failed for {yf_symbol} ({timeframe}): {e}. Generating mock.") # Debugging print
        # Fallback to mock data on API failure
        mock_df = generate_mock_stock_data_local(timeframe=timeframe)
        mock_df = calculate_technical_indicators(mock_df) # Calculate indicators for mock data too
        return mock_df

# --- News API Integration (NewsAPI.org) ---
@st.cache_data(ttl=5 * 60) # Cache for 5 minutes for news data
def get_financial_news_api(query: str, language: str = 'en', sort_by: str = 'relevancy', days_back: int = 30):
    """
    Fetches financial news articles from NewsAPI.org. Includes mock data fallback.
    """
    if not NEWS_API_KEY:
        # print("Fallback: NEWS_API_KEY not set. Returning mock news.") # Debugging print
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
        "pageSize": 20 # Limit to 20 articles
    }
    
    # --- IMPORTANT NOTE ON NEWS SOURCES ---
    # NewsAPI.org does not have distinct, reliable source IDs for Moneycontrol or Economic Times
    # that allow exclusive filtering. Articles from these sources might appear based on the 'q'
    # parameter if they are indexed by NewsAPI.org. For guaranteed exclusive content from
    # Moneycontrol and Economic Times, direct web scraping would be required, which is beyond
    # the scope of the current request due to "no new code" constraint and scraping complexities.
    # We will proceed with the general query to NewsAPI.org.
    # You might find articles from various Indian sources including potentially Moneycontrol/Economic Times.
    
    # print(f"Attempting NewsAPI.org for query: '{query}'") # Debugging print
    try:
        response = requests.get("https://newsapi.org/v2/everything", params=params, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
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
                    "event": "General News" # Default event, will be refined by perform_ner
                })
            # print(f"NewsAPI.org: Successfully fetched {len(articles)} news articles for '{query}'.") # Debugging print
            return articles
        elif data["status"] == "error":
            error_msg = data['message']
            # print(f"NewsAPI.org Error for '{query}': {error_msg}") # Debugging print
            # Specific fallback for rate limit errors
            if "maximum results for free plan" in error_msg:
                # print(f"Fallback: NewsAPI.org free plan limit. Returning mock news.") # Debugging print
                return [{
                    "source": "Mock News", "title": f"Mock News for {query} - Rate Limit",
                    "content": "This is a mock news article due to NewsAPI.org rate limits.",
                    "url": "#", "publishedAt": datetime.now().isoformat(), "event": "Mock Event"
                }]
            # General fallback for other API errors
            return [{
                "source": "Mock News", "title": f"Mock News for {query} - API Error: {error_msg}",
                "content": "News fetching failed. Using mock data.",
                "url": "#", "publishedAt": datetime.now().isoformat(), "event": "Mock Event"
            }]
    except requests.exceptions.Timeout:
        # print(f"Fallback: NewsAPI.org Timeout for '{query}'. Returning mock news.") # Debugging print
        return [{
            "source": "Mock News", "title": f"Mock News for {query} - Timeout",
            "content": "This is a mock news article due to NewsAPI.org timeout.",
            "url": "#", "publishedAt": datetime.now().isoformat(), "event": "Mock Event"
        }]
    except requests.exceptions.RequestException as e:
        # print(f"Fallback: NewsAPI.org Request failed for '{query}': {e}. Returning mock news.") # Debugging print
        return [{
            "source": "Mock News", "title": f"Mock News for {query} - Request Failed",
            "content": "This is a mock news article due to NewsAPI.org request failure.",
            "url": "#", "publishedAt": datetime.now().isoformat(), "event": "Mock Event"
        }]

# --- NEW: Technical Indicator Based Strategy Logic ---
def generate_technical_signals(df):
    """
    Generates trading signals based on technical indicators.
    Assumes df has 'Close' and calculated indicator columns.
    """
    if df.empty:
        return "HOLD", 0.0, 0.0, 0.0 # Action, Confidence, Stop Loss, Take Profit

    latest_data = df.iloc[-1]
    second_latest_data = df.iloc[-2] if len(df) > 1 else None
    
    current_close = latest_data['Close']
    
    buy_signals = 0
    sell_signals = 0
    neutral_signals = 0

    # SMA / EMA Crossover Strategy
    # Using SMA_20 and SMA_50
    if 'SMA_20' in latest_data and 'SMA_50' in latest_data and second_latest_data is not None:
        if latest_data['SMA_20'] > latest_data['SMA_50'] and second_latest_data['SMA_20'] <= second_latest_data['SMA_50']:
            buy_signals += 1 # Golden Cross
        elif latest_data['SMA_20'] < latest_data['SMA_50'] and second_latest_data['SMA_20'] >= second_latest_data['SMA_50']:
            sell_signals += 1 # Death Cross
        else:
            neutral_signals += 0.5 # Partially neutral if no clear crossover

    # RSI Strategy
    if 'RSI_14' in latest_data:
        if latest_data['RSI_14'] < 30:
            buy_signals += 1 # Oversold
        elif latest_data['RSI_14'] > 70:
            sell_signals += 1 # Overbought
        else:
            neutral_signals += 0.5

    # MACD Strategy
    # MACD line: MACD, Signal line: MACDS
    if 'MACD' in latest_data and 'MACDS' in latest_data and second_latest_data is not None:
        if latest_data['MACD'] > latest_data['MACDS'] and second_latest_data['MACD'] <= second_latest_data['MACDS']:
            buy_signals += 1 # MACD crosses above Signal
        elif latest_data['MACD'] < latest_data['MACDS'] and second_latest_data['MACD'] >= second_latest_data['MACDS']:
            sell_signals += 1 # MACD crosses below Signal
        else:
            neutral_signals += 0.5

    # Bollinger Bands Strategy
    # BBL_20_2.0 (Lower Band), BBU_20_2.0 (Upper Band)
    if 'BBL_20_2.0' in latest_data and 'BBU_20_2.0' in latest_data:
        if current_close < latest_data['BBL_20_2.0']:
            buy_signals += 1 # Price below lower band
        elif current_close > latest_data['BBU_20_2.0']:
            sell_signals += 1 # Price above upper band
        else:
            neutral_signals += 0.5

    total_signals = buy_signals + sell_signals + neutral_signals

    action = "HOLD"
    confidence = 0.5
    stop_loss_pct = 0.015 # Default 1.5%
    take_profit_pct = 0.03 # Default 3%

    if buy_signals > sell_signals and buy_signals > neutral_signals:
        action = "BUY"
        confidence = round(buy_signals / total_signals if total_signals > 0 else 0.5, 2)
        stop_loss_pct = round(np.random.uniform(2.0, 3.0), 2) / 100 # 2-3%
        take_profit_pct = round(4.0 + np.random.rand() * 2.0, 2) / 100 # 4-6%
    elif sell_signals > buy_signals and sell_signals > neutral_signals:
        action = "SELL/SHORT"
        confidence = round(sell_signals / total_signals if total_signals > 0 else 0.5, 2)
        stop_loss_pct = round(2.5 + np.random.rand() * 1.0, 2) / 100 # 2.5-3.5%
        take_profit_pct = round(5.0 + np.random.rand() * 2.0, 2) / 100 # 5-7%
    else:
        action = "HOLD"
        confidence = round(neutral_signals / total_signals if total_signals > 0 else 0.5, 2)
        stop_loss_pct = round(1.0 + np.random.rand() * 0.5, 2) / 100 # 1-1.5%
        take_profit_pct = round(1.5 + np.random.rand() * 1.0, 2) / 100 # 1.5-2.5%
    
    stop_loss = round(current_close * (1 - stop_loss_pct), 2) if action in ["BUY"] else round(current_close * (1 + stop_loss_pct), 2)
    take_profit = round(current_close * (1 + take_profit_pct), 2) if action in ["BUY"] else round(current_close * (1 - take_profit_pct), 2)

    return action, confidence, stop_loss, take_profit

# --- NEW: Combined Strategy Logic ---
def generate_combined_strategy_signal(news_signal, technical_signal, current_price):
    """
    Combines signals from news-based and technical analysis strategies.
    Prioritizes strong signals and applies a simple weighting.
    """
    news_action = news_signal["recommended_action"]
    news_confidence = news_signal["confidence"]
    news_event = news_signal["event"]

    tech_action = technical_signal[0]
    tech_confidence = technical_signal[1]

    final_action = "HOLD"
    final_confidence = 0.0
    final_stop_loss = None
    final_take_profit = None

    # Priority for Strong BUY/SELL from News (especially high-impact events)
    if "STRONG" in news_action:
        final_action = news_action
        final_confidence = news_confidence
        final_stop_loss = news_signal["stop_loss"]
        final_take_profit = news_signal["take_profit"]
        
    # If no strong news signal, consider a combination
    elif news_action == "BUY" and tech_action == "BUY":
        final_action = "BUY"
        final_confidence = (news_confidence + tech_confidence) / 2
        final_stop_loss = min(news_signal["stop_loss"], technical_signal[2]) if news_signal["stop_loss"] is not None and technical_signal[2] is not None else (news_signal["stop_loss"] or technical_signal[2])
        final_take_profit = max(news_signal["take_profit"], technical_signal[3]) if news_signal["take_profit"] is not None and technical_signal[3] is not None else (news_signal["take_profit"] or technical_signal[3])
    elif news_action == "SELL/SHORT" and tech_action == "SELL/SHORT":
        final_action = "SELL/SHORT"
        final_confidence = (news_confidence + tech_confidence) / 2
        final_stop_loss = max(news_signal["stop_loss"], technical_signal[2]) if news_signal["stop_loss"] is not None and technical_signal[2] is not None else (news_signal["stop_loss"] or technical_signal[2])
        final_take_profit = min(news_signal["take_profit"], technical_signal[3]) if news_signal["take_profit"] is not None and technical_signal[3] is not None else (news_signal["take_profit"] or technical_signal[3])
    
    # If one is BUY and other is HOLD, or both are HOLD
    elif (news_action == "BUY" and tech_action == "HOLD") or \
         (news_action == "HOLD" and tech_action == "BUY"):
        final_action = "BUY"
        final_confidence = max(news_confidence, tech_confidence) * 0.8 # Slightly reduced confidence
        final_stop_loss = news_signal["stop_loss"] if news_action == "BUY" else technical_signal[2]
        final_take_profit = news_signal["take_profit"] if news_action == "BUY" else technical_signal[3]
    elif (news_action == "SELL/SHORT" and tech_action == "HOLD") or \
         (news_action == "HOLD" and tech_action == "SELL/SHORT"):
        final_action = "SELL/SHORT"
        final_confidence = max(news_confidence, tech_confidence) * 0.8 # Slightly reduced confidence
        final_stop_loss = news_signal["stop_loss"] if news_action == "SELL/SHORT" else technical_signal[2]
        final_take_profit = news_signal["take_profit"] if news_action == "SELL/SHORT" else technical_signal[3]
    
    # Conflicting signals, default to HOLD with lower confidence
    elif (news_action == "BUY" and tech_action == "SELL/SHORT") or \
         (news_action == "SELL/SHORT" and tech_action == "BUY"):
        final_action = "HOLD"
        final_confidence = 0.3 + np.random.rand() * 0.1 # Low confidence, close to neutral
        final_stop_loss = round(current_price * (1 - 0.01), 2) # small default
        final_take_profit = round(current_price * (1 + 0.01), 2) # small default
    
    # Default HOLD if no clear signals
    else: # Both are HOLD or other ambiguous cases
        final_action = "HOLD"
        final_confidence = (news_confidence + tech_confidence) / 2 # Average confidence
        final_stop_loss = round(current_price * (1 - 0.01), 2) # small default
        final_take_profit = round(current_price * (1 + 0.01), 2) # small default

    return {
        "ticker": news_signal["ticker"],
        "sentiment": news_signal["sentiment"], # Keep news sentiment for context
        "event": news_event,
        "confidence": round(final_confidence, 2),
        "recommended_action": final_action,
        "stop_loss": final_stop_loss,
        "take_profit": final_take_profit,
        "technical_signal": tech_action, # Add tech signal for transparency
        "technical_confidence": round(tech_confidence, 2) # Add tech confidence
    }


# --- Streamlit UI Components ---

st.header(f"📈 Detailed Dashboard: {CURRENT_STOCK}")
st.write(f"Comprehensive insights for {CURRENT_STOCK} on BSE/NSE.")

# --- NEW: Auto-refresh the page every 30 seconds for live updates ---
# This will cause the entire script to re-run, fetching fresh prices/news if caches expire.
st_autorefresh(interval=30 * 1000, key=f"data_refresh_{CURRENT_STOCK}") 


# Display BSE and NSE prices
st.markdown("---")
st.subheader("Current Market Prices")

# Using st.empty() to allow for potential future granular updates if not using full page refresh
# For now, with st_autorefresh, the whole block re-renders anyway.
price_placeholder = st.empty()

# Fetch both BSE and NSE prices using yfinance directly
bse_price = get_live_stock_price_yf(CURRENT_STOCK, "BSE") # Fetches SBI price for BSE
nse_price = get_live_stock_price_yf(CURRENT_STOCK, "NSE") # Fetches SBI price for NSE

with price_placeholder.container():
    if bse_price is not None and nse_price is not None:
        st.markdown(f"""
        <div style="background-color: #f0f8ff; padding: 1rem; border-radius: 0.5rem; display: flex; justify-content: space-around; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="text-align: center;">
                <span style="font-size: 1.2rem; font-weight: bold; color: #4CAF50;">BSE:</span>
                <span style="font-size: 1.5rem; font-weight: bold; color: #333;">₹{bse_price:.2f}</span>
            </div>
            <div style="text-align: center;">
                <span style="font-size: 1.2rem; font-weight: bold; color: #2196F3;">NSE:</span>
                <span style="font-size: 1.5rem; font-weight: bold; color: #333;">₹{nse_price:.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Attempting to fetch live prices (using mock if API fails)... Please ensure internet connection and correct stock symbols.")
    
    # Get current time in IST for display
    ist_timezone = pytz.timezone('Asia/Kolkata')
    current_ist_time = datetime.now(ist_timezone)
    formatted_time = current_ist_time.strftime('%Y-%m-%d %H:%M:%S IST') # Added IST for clarity
    st.markdown(f"<p style='text-align: right; font-size: 0.8em; color: gray;'>Last updated: {formatted_time}</p>", unsafe_allow_html=True)


# Timeframe Controls
st.subheader("Select Timeframe:")
timeframe_options = ["5m", "1d", "1w", "1m", "1y"]
selected_timeframe = st.radio(
    "Timeframe",
    timeframe_options,
    index=timeframe_options.index("1y"), # Default to 1y
    horizontal=True,
    label_visibility="collapsed"
)

# Generate stock data based on selection (fetched directly here from yfinance)
stock_data = get_historical_ohlc_yf(CURRENT_STOCK, selected_timeframe, "NSE") # Assume NSE for graphs by default

# --- Graphs Section (Stacked Vertically) ---
st.markdown("---")
st.subheader(f"Price Charts and Technical Indicators for {CURRENT_STOCK}")

if not stock_data.empty:
    # Candlestick Chart with Moving Averages
    st.markdown("### Candlestick Chart with SMAs")
    fig_candlestick = go.Figure(data=[go.Candlestick(
        x=stock_data.index, # Use index (Date) for x-axis
        open=stock_data['Open'],
        high=stock_data['High'],
        low=stock_data['Low'],
        close=stock_data['Close'],
        increasing_line_color='green',
        decreasing_line_color='red',
        name='Candlestick'
    )])
    # Add SMA_20 and SMA_50
    if 'SMA_20' in stock_data.columns:
        fig_candlestick.add_trace(go.Scatter(x=stock_data.index, y=stock_data['SMA_20'],
                                            mode='lines', name='SMA 20', line=dict(color='blue', width=1)))
    if 'SMA_50' in stock_data.columns:
        fig_candlestick.add_trace(go.Scatter(x=stock_data.index, y=stock_data['SMA_50'],
                                            mode='lines', name='SMA 50', line=dict(color='orange', width=1)))
    fig_candlestick.update_layout(
        xaxis_rangeslider_visible=False,
        xaxis_title="Date",
        yaxis_title="Price (₹)",
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(x=0, y=1.05, xanchor='left', yanchor='bottom', orientation='h')
    )
    st.plotly_chart(fig_candlestick, use_container_width=True)

    # RSI Chart
    if 'RSI_14' in stock_data.columns:
        st.markdown("### Relative Strength Index (RSI)")
        fig_rsi = go.Figure(go.Scatter(x=stock_data.index, y=stock_data['RSI_14'],
                                       mode='lines', name='RSI 14', line=dict(color='purple')))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
        fig_rsi.update_layout(
            xaxis_title="Date",
            yaxis_title="RSI Value",
            height=250,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_rsi, use_container_width=True)

    # MACD Chart
    if 'MACD' in stock_data.columns and 'MACDH' in stock_data.columns and 'MACDS' in stock_data.columns:
        st.markdown("### Moving Average Convergence Divergence (MACD)")
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=stock_data.index, y=stock_data['MACD'],
                                       mode='lines', name='MACD Line', line=dict(color='blue')))
        fig_macd.add_trace(go.Scatter(x=stock_data.index, y=stock_data['MACDS'],
                                       mode='lines', name='Signal Line', line=dict(color='red')))
        fig_macd.add_trace(go.Bar(x=stock_data.index, y=stock_data['MACDH'],
                                   name='Histogram', marker_color='gray', opacity=0.6))
        fig_macd.update_layout(
            xaxis_title="Date",
            yaxis_title="MACD Value",
            height=250,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(x=0, y=1.05, xanchor='left', yanchor='bottom', orientation='h')
        )
        st.plotly_chart(fig_macd, use_container_width=True)

    # Bollinger Bands Chart
    if 'BBL_20_2.0' in stock_data.columns and 'BBM_20_2.0' in stock_data.columns and 'BBU_20_2.0' in stock_data.columns:
        st.markdown("### Bollinger Bands")
        fig_bb = go.Figure()
        fig_bb.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Close'],
                                     mode='lines', name='Close Price', line=dict(color='#4f46e5', width=2)))
        fig_bb.add_trace(go.Scatter(x=stock_data.index, y=stock_data['BBU_20_2.0'],
                                     mode='lines', name='Upper Band', line=dict(color='grey', dash='dash')))
        fig_bb.add_trace(go.Scatter(x=stock_data.index, y=stock_data['BBM_20_2.0'],
                                     mode='lines', name='Middle Band', line=dict(color='purple', dash='dot')))
        fig_bb.add_trace(go.Scatter(x=stock_data.index, y=stock_data['BBL_20_2.0'],
                                     mode='lines', name='Lower Band', line=dict(color='grey', dash='dash')))
        fig_bb.update_layout(
            xaxis_title="Date",
            yaxis_title="Price (₹)",
            height=250,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(x=0, y=1.05, xanchor='left', yanchor='bottom', orientation='h')
        )
        st.plotly_chart(fig_bb, use_container_width=True)
else:
    st.warning(f"No stock data available for {CURRENT_STOCK} for the selected timeframe. Check yfinance compatibility for this symbol.")


# --- News Feed Section (fetched directly and processed) ---
st.markdown("---")
st.subheader(f"Latest News for {CURRENT_STOCK}")

# Fetch news and analysis directly
raw_articles = get_financial_news_api(f"{CURRENT_STOCK} stock") # Pass query for SBI news

processed_news = []
latest_news_signal_data = { # This will hold the news-based signal for the combined strategy
    "ticker": CURRENT_STOCK,
    "sentiment": "N/A",
    "event": "N/A",
    "confidence": 0.00,
    "recommended_action": "HOLD",
    "stop_loss": None,
    "take_profit": None
}

if not raw_articles:
    st.info(f"No news found for {CURRENT_STOCK}.")
else:
    # Define IST timezone once
    ist_timezone = pytz.timezone('Asia/Kolkata')

    for i, news_item in enumerate(raw_articles):
        full_text = f"{news_item.get('title', '')} {news_item.get('content', '')}"
        
        # Perform NLP and action mapping directly
        ticker_identified, event_identified = perform_ner(full_text, CURRENT_STOCK) # Get both
        sentiment = analyze_sentiment(full_text)
        action_data = map_news_to_action(sentiment, event_identified, current_price=nse_price) # Pass current price

        # Convert publishedAt to IST
        published_utc_str = news_item.get("publishedAt", "N/A")
        published_ist_str = "N/A"
        if published_utc_str != "N/A":
            try:
                # Parse the UTC timestamp provided by NewsAPI (e.g., "YYYY-MM-DDTHH:MM:SSZ")
                published_utc = datetime.strptime(published_utc_str, '%Y-%m-%dT%H:%M:%SZ')
                # Make it timezone-aware (as UTC) and then convert to IST
                published_ist = published_utc.replace(tzinfo=pytz.utc).astimezone(ist_timezone)
                published_ist_str = published_ist.strftime('%Y-%m-%d %H:%M:%S IST')
            except ValueError:
                # Handle cases where publishedAt might be in a different format or invalid
                published_ist_str = f"Invalid Date Format: {published_utc_str}"


        processed_news_item = {
            "source": news_item["source"],
            "title": news_item["title"],
            "content": news_item["content"],
            "url": news_item["url"],
            "publishedAt": published_ist_str, # Use IST formatted string here
            "sentiment": sentiment,
            "event": event_identified, # Use the identified event
            "recommended_action": action_data["recommended_action"],
            "confidence": action_data["confidence"]
        }
        processed_news.append(processed_news_item)

        # For the latest news signal, use the first article's analysis
        if i == 0:
            latest_news_signal_data = {
                "ticker": ticker_identified,
                "sentiment": sentiment,
                "event": event_identified,
                "confidence": action_data["confidence"],
                "recommended_action": action_data["recommended_action"],
                "stop_loss": action_data["stop_loss"],
                "take_profit": action_data["take_profit"]
            }

    # Display news articles in two columns
    news_col1, news_col2 = st.columns(2)
    for i, news in enumerate(processed_news):
        # HTML for each news card, with dynamic styling based on sentiment/action
        news_html = f"""
        <div style="background-color: #ffffff; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);">
            <p style="font-size: 0.75rem; color: #6b7280;">{news['source']} | {news['event']} | {news['publishedAt']}</p> 
            <h3 style="font-size: 1rem; font-weight: 600; color: #1f2937;">{news['title']}</h3>
            <p style="font-size: 0.875rem; color: #374151;">{news['content'][:250]}...</p>
            <p style="font-size: 0.75rem;"><a href="{news['url']}" target="_blank" style="color: #4f46e5;">Read more</a></p>
            <div style="display: flex; align-items: center; margin-top: 0.5rem; font-size: 0.875rem;">
                <span style="font-weight: 500;">Sentiment:</span>
                <span style="font-weight: 700; color: {'#16a34a' if news['sentiment'] == 'positive' else ('#dc2626' if news['sentiment'] == 'negative' else '#f59e0b')}; margin-left: 0.25rem;">
                                {news['sentiment'].upper()}
                            </span>
                            <span style="font-weight: 500; margin-left: 1rem;">Action:</span>
                            <span style="font-weight: 700; color: {'#16a34a' if news['recommended_action'] == 'BUY' or news['recommended_action'] == 'STRONG BUY' else ('#dc2626' if news['recommended_action'] == 'SELL/SHORT' or news['recommended_action'] == 'STRONG SELL' else '#3b82f6')}; margin-left: 0.25rem;">
                                {news['recommended_action']}
                            </span>
                        </div>
                    </div>
                    """
        # Distribute news articles into two columns
        if i % 2 == 0:
            with news_col1:
                st.markdown(news_html, unsafe_allow_html=True)
        else:
            with news_col2:
                st.markdown(news_html, unsafe_allow_html=True)

# --- Trading Bot Signal Output (Combined Strategy) ---
st.markdown("---")
st.subheader("Trading Bot Signal (Simulated)")

# Generate technical signal based on the latest historical data (if available)
technical_signal = ("HOLD", 0.0, None, None) # Default values
if not stock_data.empty:
    technical_signal = generate_technical_signals(stock_data)

# Generate combined signal
combined_trading_signal = generate_combined_strategy_signal(
    latest_news_signal_data,
    technical_signal,
    nse_price # Pass current NSE price for SL/TP calculation
)

st.write("This structured JSON output is generated by the combined Technical and News strategies.")
# Display the combined trading signal in JSON format
st.code(f"""
{{
    "ticker": "{combined_trading_signal['ticker']}",
    "combined_action": "{combined_trading_signal['recommended_action']}",
    "combined_confidence": {combined_trading_signal['confidence']:.2f},
    "stop_loss": {combined_trading_signal['stop_loss']:.2f} if {combined_trading_signal['stop_loss'] is not None} else "N/A",
    "take_profit": {combined_trading_signal['take_profit']:.2f} if {combined_trading_signal['take_profit'] is not None} else "N/A",
    "news_sentiment": "{combined_trading_signal['sentiment']}",
    "news_event": "{combined_trading_signal['event']}",
    "technical_signal_from_indicators": "{combined_trading_signal['technical_signal']}",
    "technical_confidence": {combined_trading_signal['technical_confidence']:.2f}
}}
""", language='json')