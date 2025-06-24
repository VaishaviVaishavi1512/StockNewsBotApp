# pages/BEL.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import yfinance as yf # Import yfinance directly
import os # To access environment variables if st.secrets not used (for local testing mostly)
import pytz # NEW: Import pytz for timezone handling
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import re

# Load FinBERT
@st.cache_resource
def load_finbert():
    tokenizer = AutoTokenizer.from_pretrained("yiyanghkust/finbert-tone")
    model = AutoModelForSequenceClassification.from_pretrained("yiyanghkust/finbert-tone")
    return tokenizer, model

finbert_tokenizer, finbert_model = load_finbert()

def analyze_with_finbert(text):
    inputs = finbert_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    outputs = finbert_model(**inputs)
    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
    sentiment = torch.argmax(probs).item()
    labels = ['negative', 'neutral', 'positive']
    return labels[sentiment], round(probs[0][sentiment].item(), 2)



# --- NEW: Import streamlit_autorefresh for live updates ---
from streamlit_autorefresh import st_autorefresh

# --- Stock-Specific Configuration ---
CURRENT_STOCK = "BEL"
FULL_STOCK_NAME = "Bharat Electronics Limited" # Added for better display

# --- API Key Configuration (for Streamlit Cloud: use st.secrets) ---
NEWS_API_KEY = st.secrets.get("NEWS_API_KEY")

if not NEWS_API_KEY:
    st.warning("NewsAPI.org API Key not found. News data will be mocked. "
                "Please add it to your Streamlit secrets or environment variables.")

# --- NLP and Action Mapping Functions (Directly in Streamlit app) ---
def perform_ner(text, current_stock_symbol):
    text_lower = text.lower()

    stock_aliases = {
        "IRCTC": ["irctc", "indian railways catering", "railways"],
        "SBI": ["sbi", "state bank of india"],
        "TATA MOTORS": ["tata motors", "tata"],
        "BEL": ["bharat electronics", "bel"],
        "INDIGO AIRLINES": ["indigo airlines", "indigo", "interglobe aviation"]
    }

    # First, check if current stock is mentioned
    current_aliases = stock_aliases.get(current_stock_symbol.upper(), [])
    current_mentioned = any(alias in text_lower for alias in current_aliases)

    if current_mentioned:
        return current_stock_symbol

    # Only if current stock is not mentioned, check for other stocks
    for stock_sym, aliases in stock_aliases.items():
        if stock_sym != current_stock_symbol:
            if any(alias in text_lower for alias in aliases):
                return stock_sym

    # Fallback: assume it's about the current stock
    return current_stock_symbol



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

# --- Mock Data Generation (Fallback if yfinance/NewsAPI fail) ---
def generate_mock_stock_data_local(timeframe, num_points_override=None):
    data = []
    last_close = np.random.uniform(250, 270) # Adjusted range for BEL's typical price
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
            'Volume': int(np.random.randint(1000000, 10000000)) # Adjusted volume for BEL
        })
        last_close = close_price
    return pd.DataFrame(data)

# --- Financial Data Integration (yfinance) ---
def get_yfinance_symbol(symbol: str, exchange: str = "NSE"):
    # Updated mapping based on the user's provided simplified function for BEL
    symbol_map = {
        "IRCTC": "IRCTC.NS",
        "SBI": "SBIN.NS",
        "TATA MOTORS": "TATAMOTORS.NS",
        "BEL": "BEL.NS", # Explicitly for BEL
        "INDIGO AIRLINES": "INDIGO.NS"
    }
    
    yf_base_symbol = symbol_map.get(symbol.upper(), symbol) # Use mapped symbol if available

    if exchange.upper() == "NSE": return f"{yf_base_symbol}"
    elif exchange.upper() == "BSE":
        if not yf_base_symbol.endswith(".NS") and not yf_base_symbol.endswith(".BO"):
            return f"{yf_base_symbol}.BO"
        return yf_base_symbol
    return yf_base_symbol # Fallback

@st.cache_data(ttl=30) # Cache for 30 seconds for "live" price. St_autorefresh will trigger.
def get_live_stock_price_yf(symbol: str, exchange: str = "NSE"):
    yf_symbol = get_yfinance_symbol(symbol, exchange)
    print(f"Attempting yfinance live price for: {yf_symbol}")
    try:
        ticker = yf.Ticker(yf_symbol)
        # Use 'regularMarketPrice' for current price
        live_price = ticker.info.get('regularMarketPrice')
        # Fallback to 'currentPrice' or 'dayHigh'/'dayLow' if market is closed or info incomplete
        if live_price is None:
            live_price = ticker.info.get('currentPrice')
        if live_price is None:
            # As a last resort, take the last close from recent history if nothing else works
            hist_data = ticker.history(period="1d", interval="1m")
            if not hist_data.empty:
                live_price = hist_data['Close'].iloc[-1]


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

st.header(f"📈 Detailed Dashboard: {FULL_STOCK_NAME} ({CURRENT_STOCK})") # Updated header
st.write(f"Comprehensive insights for {FULL_STOCK_NAME} on BSE/NSE.")

# --- NEW: Auto-refresh the page every 30 seconds for live updates ---
# This will cause the entire script to re-run, fetching fresh prices/news if caches expire.
st_autorefresh(interval=30 * 1000, key=f"data_refresh_{CURRENT_STOCK}")    


# Display BSE and NSE prices (fetched directly here from yfinance)
st.markdown("---")
st.subheader("Current Market Prices")

price_placeholder = st.empty()

# Fetch both BSE and NSE prices using yfinance directly
bse_price = get_live_stock_price_yf(CURRENT_STOCK, "BSE")
nse_price = get_live_stock_price_yf(CURRENT_STOCK, "NSE")

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
st.subheader(f"Price Charts for {FULL_STOCK_NAME} ({CURRENT_STOCK})") # Updated header

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


# --- News Section with FinBERT & NER Filtering ---
st.markdown("---")
st.subheader("📰 Latest Financial News (Filtered & Analyzed)")

raw_articles = get_financial_news_api(f"{FULL_STOCK_NAME} stock", language="en", sort_by="relevancy", days_back=30)

relevant_articles = []
latest_trading_signal = {
    "ticker": CURRENT_STOCK,
    "sentiment": "N/A",
    "event": "N/A",
    "confidence": 0.00,
    "recommended_action": "HOLD",
    "stop_loss": 0.00,
    "take_profit": 0.00
}

ist_timezone = pytz.timezone('Asia/Kolkata')

for i, article in enumerate(raw_articles):
    content = article.get("content", "") or ""
    full_text = f"{article.get('title', '')} {content}"
    if not content:
        continue

    # Check if the article is actually about this stock
    if perform_ner(full_text, CURRENT_STOCK) != CURRENT_STOCK:
        continue

    sentiment, confidence = analyze_with_finbert(full_text)
    if confidence < 0.6:
        continue

    # Convert time to IST
    published_ist_str = "N/A"
    try:
        published_utc = datetime.strptime(article["publishedAt"], '%Y-%m-%dT%H:%M:%SZ')
        published_ist = published_utc.replace(tzinfo=pytz.utc).astimezone(ist_timezone)
        published_ist_str = published_ist.strftime('%Y-%m-%d %H:%M:%S IST')
    except:
        pass

    action_data = map_news_to_action(sentiment)

    if i == 0:
        latest_trading_signal = {
            "ticker": CURRENT_STOCK,
            "sentiment": sentiment,
            "event": article.get("event", "General News"),
            "confidence": confidence,
            "recommended_action": action_data["recommended_action"],
            "stop_loss": action_data["stop_loss"],
            "take_profit": action_data["take_profit"]
        }

    relevant_articles.append({
        "source": article.get("source", "Unknown"),
        "title": article.get("title", "No Title"),
        "content": content,
        "url": article.get("url", "#"),
        "publishedAt": published_ist_str,
        "sentiment": sentiment,
        "confidence": confidence,
        "recommended_action": action_data["recommended_action"]
    })

if relevant_articles:
    news_col1, news_col2 = st.columns(2)
    for i, news in enumerate(relevant_articles):
        news_html = f"""
        <div style="background-color: #ffffff; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);">
            <p style="font-size: 0.75rem; color: #6b7280;">{news['source']} | {news['publishedAt']}</p>    
            <h3 style="font-size: 1rem; font-weight: 600; color: #1f2937;">{news['title']}</h3>
            <p style="font-size: 0.875rem; color: #374151;">{news['content'][:250]}...</p>
            <p style="font-size: 0.75rem;"><a href="{news['url']}" target="_blank" style="color: #4f46e5;">Read more</a></p>
            <div style="display: flex; align-items: center; margin-top: 0.5rem; font-size: 0.875rem;">
                <span style="font-weight: 500;">Sentiment:</span>
                <span style="font-weight: 700; color: {'#16a34a' if news['sentiment'] == 'positive' else ('#dc2626' if news['sentiment'] == 'negative' else '#f59e0b')}; margin-left: 0.25rem;">
                    {news['sentiment'].upper()} ({news['confidence']*100:.0f}%)
                </span>
                <span style="font-weight: 500; margin-left: 1rem;">Action:</span>
                <span style="font-weight: 700; color: {'#16a34a' if news['recommended_action'] == 'BUY' else ('#dc2626' if news['recommended_action'] == 'SELL/SHORT' else '#3b82f6')}; margin-left: 0.25rem;">
                    {news['recommended_action']}
                </span>
            </div>
        </div>
        """
        (news_col1 if i % 2 == 0 else news_col2).markdown(news_html, unsafe_allow_html=True)
else:
    st.info("No relevant, high-confidence BEL news found from NewsAPI in the last 30 days.")

# --- Strategy Decision Engine ---
st.markdown("---")
st.markdown("## 🧠 Strategy Decision Engine")

import ta

# Ensure stock_data has no NaNs and is sorted
strategy_data = stock_data.copy().dropna()
strategy_data.sort_index(inplace=True)

signals_summary = []  # Store individual strategy results

# --- 1. EMA Crossover ---
ema20 = ta.trend.ema_indicator(strategy_data['Close'], window=20).fillna(0)
ema50 = ta.trend.ema_indicator(strategy_data['Close'], window=50).fillna(0)
ema_signal = "BUY" if ema20.iloc[-1] > ema50.iloc[-1] else "SELL"
signals_summary.append(ema_signal)

with st.container():
    st.markdown("""
    <div style='background-color: #ecfdf5; padding: 1rem; border-radius: 0.5rem;'>
        <h4>📊 <strong>EMA Strategy Signal</strong></h4>
        <p><strong>20 EMA:</strong> ₹{:.2f} | <strong>50 EMA:</strong> ₹{:.2f}</p>
        <p><strong>Signal:</strong> {}</p>
    </div>
    """.format(ema20.iloc[-1], ema50.iloc[-1], ema_signal), unsafe_allow_html=True)

# --- 2. SMA Crossover ---
sma20 = ta.trend.sma_indicator(strategy_data['Close'], window=20).fillna(0)
sma50 = ta.trend.sma_indicator(strategy_data['Close'], window=50).fillna(0)
sma_signal = "BUY" if sma20.iloc[-1] > sma50.iloc[-1] else "SELL"
signals_summary.append(sma_signal)

st.markdown("""
<div style='background-color: #f0fdf4; padding: 1rem; border-radius: 0.5rem;'>
    <h4>📊 <strong>SMA Strategy Signal</strong></h4>
    <p><strong>20 SMA:</strong> ₹{:.2f} | <strong>50 SMA:</strong> ₹{:.2f}</p>
    <p><strong>Signal:</strong> {}</p>
</div>
""".format(sma20.iloc[-1], sma50.iloc[-1], sma_signal), unsafe_allow_html=True)

# --- 3. RSI Strategy ---
rsi = ta.momentum.RSIIndicator(strategy_data['Close'], window=14).rsi().fillna(50)
rsi_signal = "BUY" if rsi.iloc[-1] < 30 else ("SELL" if rsi.iloc[-1] > 70 else "HOLD")
signals_summary.append(rsi_signal)

st.markdown("""
<div style='background-color: #fefce8; padding: 1rem; border-radius: 0.5rem;'>
    <h4>📉 <strong>RSI Signal</strong></h4>
    <p><strong>RSI:</strong> {:.2f}</p>
    <p><strong>Signal:</strong> {}</p>
</div>
""".format(rsi.iloc[-1], rsi_signal), unsafe_allow_html=True)

# --- 4. MACD ---
macd_line = ta.trend.macd_diff(strategy_data['Close']).fillna(0)
macd_signal = "BUY" if macd_line.iloc[-1] > 0 else "SELL"
signals_summary.append(macd_signal)

st.markdown("""
<div style='background-color: #f0f9ff; padding: 1rem; border-radius: 0.5rem;'>
    <h4>📈 <strong>MACD Signal</strong></h4>
    <p><strong>MACD:</strong> {:.4f}</p>
    <p><strong>Signal:</strong> {}</p>
</div>
""".format(macd_line.iloc[-1], macd_signal), unsafe_allow_html=True)

# --- 5. Bollinger Bands ---
bbands = ta.volatility.BollingerBands(strategy_data['Close'], window=20)
bb_lower = bbands.bollinger_lband().iloc[-1]
bb_upper = bbands.bollinger_hband().iloc[-1]
bb_signal = "BUY" if strategy_data['Close'].iloc[-1] < bb_lower else ("SELL" if strategy_data['Close'].iloc[-1] > bb_upper else "HOLD")
signals_summary.append(bb_signal)

st.markdown("""
<div style='background-color: #fff7ed; padding: 1rem; border-radius: 0.5rem;'>
    <h4>📊 <strong>Bollinger Bands</strong></h4>
    <p><strong>Close:</strong> ₹{:.2f} | <strong>Lower Band:</strong> ₹{:.2f} | <strong>Upper Band:</strong> ₹{:.2f}</p>
    <p><strong>Signal:</strong> {}</p>
</div>
""".format(strategy_data['Close'].iloc[-1], bb_lower, bb_upper, bb_signal), unsafe_allow_html=True)

# --- 6. News-Based Strategy ---
news_sentiment_signal = latest_trading_signal.get("recommended_action", "HOLD")
signals_summary.append(news_sentiment_signal)

st.markdown("""
<div style='background-color: #ede9fe; padding: 1rem; border-radius: 0.5rem;'>
    <h4>📰 <strong>News-Based Sentiment Signal</strong></h4>
    <p><strong>Sentiment:</strong> {} | <strong>Confidence:</strong> {}</p>
    <p><strong>Signal:</strong> {}</p>
</div>
""".format(latest_trading_signal['sentiment'], latest_trading_signal['confidence'], news_sentiment_signal), unsafe_allow_html=True)

# --- Final Aggregated Decision ---
from collections import Counter
vote_count = Counter(signals_summary)
final_signal = vote_count.most_common(1)[0][0]

st.markdown("""
<div style='background-color: #dcfce7; padding: 1rem; border-radius: 0.5rem; margin-top: 1rem;'>
    <h3>🧾 <strong>Final Trading Decision</strong></h3>
    <p><strong>Signals Summary:</strong> {}</p>
    <p><strong>Majority Vote:</strong> <span style='color: #065f46; font-weight: bold;'>{}</span></p>
</div>
""".format(signals_summary, final_signal), unsafe_allow_html=True)

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