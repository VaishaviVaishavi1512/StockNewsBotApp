# pages/SBI.py # Changed file name
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import yfinance as yf
import os

# --- Stock-Specific Configuration ---
CURRENT_STOCK = "SBI" # Changed from "IRCTC" to "SBI"

# --- API Key Configuration (for Streamlit Cloud: use st.secrets) ---
NEWS_API_KEY = st.secrets.get("NEWS_API_KEY")

if not NEWS_API_KEY:
    st.warning("NewsAPI.org API Key not found. News data will be mocked. "
                "Please add it to your Streamlit secrets or environment variables.")

# --- NLP and Action Mapping Functions (Directly in Streamlit app) ---
def perform_ner(text, current_stock_symbol):
    text_lower = text.lower()
    # Updated keywords for SBI, keeping generic ones for other stocks
    if current_stock_symbol.lower() in text_lower or \
       "state bank of india" in text_lower or \
       "sbi" in text_lower or \
       "indian railways catering" in text_lower or \
       "tata motors" in text_lower or \
       "bharat electronics" in text_lower or \
       "indigo airlines" in text_lower or \
       "bel" in text_lower or \
       "irctc" in text_lower: # Added irctc back for broader keyword matching
        return current_stock_symbol
    return "N/A"

def analyze_sentiment(text):
    # These keywords are generally applicable to most companies, including banks.
    # You could add specific banking terms if you want more fine-grained analysis for banks.
    positive_keywords = ["profit", "soar", "jump", "rises", "invest", "contract", "boosts", "growth", "strong", "improves", "expands", "dividend", "bullish", "exceeding expectations", "robust", "healthy", "gains", "partnership", "collaboration", "launch", "loan growth", "deposit growth", "asset quality improves", "NPA reduction", "credit expansion"] # Added banking specific positive keywords
    negative_keywords = ["loss", "headwinds", "rising fuel", "supply chain issues", "missed", "resigned", "downgrade", "decline", "fall", "struggle", "uncertainty", "volatility", "challenges", "NPA increase", "fraud", "scam", "regulatory fine"] # Added banking specific negative keywords
    neutral_keywords = ["board approves", "plans", "announces", "decision", "discussions", "talks", "quarterly results", "RBI", "policy", "interest rates"] # Added banking specific neutral keywords

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

# --- Mock Data Generation (Fallback if yfinance/NewsAPI fail) ---
def generate_mock_stock_data_local(timeframe, num_points_override=None):
    data = []
    # Adjusted initial price range for SBI (typically lower than IRCTC's current values)
    last_close = np.random.uniform(600, 700) 
    interval_seconds = 0
    num_points = 0

    if timeframe == '5m': interval_seconds = 5 * 60; num_points = 60
    elif timeframe == '1d': interval_seconds = 60 * 60; num_points = 8
    elif timeframe == '1w': interval_seconds = 24 * 60 * 60; num_points = 5
    elif timeframe == '1m': interval_seconds = 24 * 60 * 60; num_points = 20
    elif timeframe == '1y': interval_seconds = 24 * 60 * 60; num_points = 250
    if num_points_override: num_points = num_points_override

    current_date = datetime.now()
    start_date = current_date - timedelta(seconds=(num_points - 1) * interval_seconds)

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
        last_close = close_price
    return pd.DataFrame(data)

# --- Financial Data Integration (yfinance) ---
def get_yfinance_symbol(symbol: str, exchange: str = "NSE"):
    # SBI's symbol on NSE is SBIN.NS, and on BSE is SBIN.BO
    if symbol.upper() == "SBI":
        if exchange.upper() == "NSE": return "SBIN.NS" # Specific symbol for SBI on NSE
        elif exchange.upper() == "BSE": return "SBIN.BO" # Specific symbol for SBI on BSE
    if exchange.upper() == "NSE": return f"{symbol}.NS"
    elif exchange.upper() == "BSE": return f"{symbol}.BO"
    return symbol

@st.cache_data(ttl=5 * 60) # Cache for 5 minutes
def get_live_stock_price_yf(symbol: str, exchange: str = "NSE"):
    yf_symbol = get_yfinance_symbol(symbol, exchange)
    print(f"Attempting yfinance live price for: {yf_symbol}")
    try:
        ticker = yf.Ticker(yf_symbol)
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

@st.cache_data(ttl=15 * 60) # Cache for 15 minutes
def get_historical_ohlc_yf(symbol: str, timeframe: str, exchange: str = "NSE"):
    yf_symbol = get_yfinance_symbol(symbol, exchange)
    print(f"Attempting yfinance historical data for: {yf_symbol} ({timeframe})")

    period_map = {'5m': '1d', '1d': '5d', '1w': '1mo', '1m': '3mo', '1y': '1y'}
    interval_map = {'5m': '5m', '1d': '60m', '1w': '1d', '1m': '1d', '1y': '1d'}

    period = period_map.get(timeframe, '1y')
    interval = interval_map.get(timeframe, '1d')

    try:
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=period, interval=interval)

        if not df.empty:
            df = df.rename(columns={"Open": "Open", "High": "High", "Low": "Low", "Close": "Close", "Volume": "Volume"})
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            df.index.name = 'Date'
            print(f"yfinance: Successfully fetched {len(df)} historical points for {yf_symbol} ({timeframe}).")
            return df
        else:
            print(f"yfinance: No historical data found for {yf_symbol} ({timeframe}). Generating mock.")
            return generate_mock_stock_data_local(timeframe=timeframe)
    except Exception as e:
        print(f"Fallback: yfinance historical data failed for {yf_symbol} ({timeframe}): {e}. Generating mock.")
        return generate_mock_stock_data_local(timeframe=timeframe)

# --- News API Integration (NewsAPI.org) ---
@st.cache_data(ttl=5 * 60) # Cache for 5 minutes
def get_financial_news_api(query: str, language: str = 'en', sort_by: str = 'relevancy', days_back: int = 30):
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
            return [{ # Fallback for other NewsAPI errors
                "source": "Mock News", "title": f"Mock News for {query} - API Error: {error_msg}",
                "content": "News fetching failed. Using mock data.",
                "url": "#", "publishedAt": datetime.now().isoformat(), "event": "Mock Event"
            }]
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


# --- Streamlit UI Components ---

st.header(f"📈 Detailed Dashboard: {CURRENT_STOCK}")
st.write(f"Comprehensive insights for {CURRENT_STOCK} on BSE/NSE.")

# Display BSE and NSE prices (fetched directly here from yfinance)
st.markdown("---")
st.subheader("Current Market Prices")

# Fetch both BSE and NSE prices using yfinance directly
# Use specific symbols for BSE/NSE if known to yfinance
bse_price = get_live_stock_price_yf(CURRENT_STOCK, "BSE") 
nse_price = get_live_stock_price_yf(CURRENT_STOCK, "NSE") 

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
st.subheader(f"Price Charts for {CURRENT_STOCK}")

if not stock_data.empty:
    # Candlestick Chart
    st.markdown("### Candlestick Chart")
    fig_candlestick = go.Figure(data=[go.Candlestick(
        x=stock_data.index, # Use index (Date) for x-axis
        open=stock_data['Open'],
        high=stock_data['High'],
        low=stock_data['Low'],
        close=stock_data['Close'],
        increasing_line_color='green',
        decreasing_line_color='red'
    )])
    fig_candlestick.update_layout(
        xaxis_rangeslider_visible=False,
        xaxis_title="Date",
        yaxis_title="Price (₹)",
        height=400,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig_candlestick, use_container_width=True)

    # Normal Line Graph
    st.markdown("### Normal Line Graph (Close Price)")
    fig_line = go.Figure(data=go.Scatter(
        x=stock_data.index, # Use index (Date) for x-axis
        y=stock_data['Close'],
        mode='lines',
        line=dict(color='#4f46e5', width=2)
    ))
    fig_line.update_layout(
        xaxis_title="Date",
        yaxis_title="Close Price (₹)",
        height=400,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.warning(f"No stock data available for {CURRENT_STOCK} for the selected timeframe. Check yfinance compatibility for this symbol.")


# --- News Feed Section (fetched directly and processed) ---
st.markdown("---")
st.subheader(f"Latest News for {CURRENT_STOCK}")

# Fetch news and analysis directly
# Changed news query to be more specific for SBI
raw_articles = get_financial_news_api(f"State Bank of India OR SBI stock") 

processed_news = []
latest_trading_signal = {
    "ticker": CURRENT_STOCK,
    "sentiment": "N/A",
    "event": "N/A",
    "confidence": 0.00,
    "recommended_action": "HOLD",
    "stop_loss": 0.00,
    "take_profit": 0.00
}

if not raw_articles:
    st.info(f"No news found for {CURRENT_STOCK}.")
else:
    for i, news_item in enumerate(raw_articles):
        full_text = f"{news_item.get('title', '')} {news_item.get('content', '')}"
        
        # Perform NLP and action mapping directly
        ticker_identified = perform_ner(full_text, CURRENT_STOCK)
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

        # For the trading bot output, use the first article as the 'latest'
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

    news_col1, news_col2 = st.columns(2)
    for i, news in enumerate(processed_news):
        news_html = f"""
        <div style="background-color: #ffffff; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);">
            <p style="font-size: 0.75rem; color: #6b7280;">{news['source']} | {news['event']} | {news['publishedAt'][:10]}</p>
            <h3 style="font-size: 1rem; font-weight: 600; color: #1f2937;">{news['title']}</h3>
            <p style="font-size: 0.875rem; color: #374151;">{news['content'][:250]}...</p>
            <p style="font-size: 0.75rem;"><a href="{news['url']}" target="_blank" style="color: #4f46e5;">Read more</a></p>
            <div style="display: flex; align-items: center; margin-top: 0.5rem; font-size: 0.875rem;">
                <span style="font-weight: 500;">Sentiment:</span>
                <span style="font-weight: 700; color: {'#16a34a' if news['sentiment'] == 'positive' else ('#dc2626' if news['sentiment'] == 'negative' else '#f59e0b')}; margin-left: 0.25rem;">
                                {news['sentiment'].upper()}
                            </span>
                            <span style="font-weight: 500; margin-left: 1rem;">Action:</span>
                            <span style="font-weight: 700; color: {'#16a34a' if news['recommended_action'] == 'BUY' else ('#dc2626' if news['recommended_action'] == 'SELL/SHORT' else '#3b82f6')}; margin-left: 0.25rem;">
                                {news['recommended_action']}
                            </span>
                        </div>
                    </div>
                    """
        if i % 2 == 0:
            with news_col1:
                st.markdown(news_html, unsafe_allow_html=True)
        else:
            with news_col2:
                st.markdown(news_html, unsafe_allow_html=True)

# --- Trading Bot Signal Output ---
st.markdown("---")
st.subheader("Trading Bot Signal (Simulated)")
st.write("This structured JSON output is generated directly by your Streamlit app.")
st.code(f"""
{{
    "ticker": "{latest_trading_signal['ticker']}",
    "sentiment": "{latest_trading_signal['sentiment']}",
    "event": "{latest_trading_signal['event']}",
    "confidence": {latest_trading_signal['confidence']},
    "recommended_action": "{latest_trading_signal['recommended_action']}",
    "stop_loss": {latest_trading_signal['stop_loss']},
    "take_profit": {latest_trading_signal['take_profit']}
}}
""", language='json')