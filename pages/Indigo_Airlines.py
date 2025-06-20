# pages/indigo_airlines.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import yfinance as yf
import os
import pytz
import json # <--- ADD THIS LINE
from streamlit_autorefresh import st_autorefresh

# --- NEW: Import pandas_ta for technical indicators ---
import pandas_ta as ta

# --- Stock-Specific Configuration ---
CURRENT_STOCK = "INDIGO AIRLINES"

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
        "BHARAT ELECTRONICS": ["bharat electronics", "bel"],
        "INDIGO AIRLINES": ["indigo airlines", "indigo", "interglobe aviation"]
    }

    for alias in stock_aliases.get(current_stock_symbol.upper(), []):
        if alias in text_lower:
            return current_stock_symbol

    for stock_sym, aliases in stock_aliases.items():
        if stock_sym != current_stock_symbol and any(alias in text_lower for alias in aliases):
            return stock_sym

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

# --- Mock Data Generation (Fallback if yfinance/NewsAPI fail) ---
def generate_mock_stock_data_local(timeframe, num_points_override=None):
    data = []
    last_close = np.random.uniform(2500, 2800)
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
    symbol_map = {
        "IRCTC": "IRCTC.NS",
        "SBI": "SBIN.NS",
        "TATA MOTORS": "TATAMOTORS.NS",
        "BHARAT ELECTRONICS": "BEL.NS",
        "INDIGO AIRLINES": "INDIGO.NS"
    }

    yf_base_symbol = symbol_map.get(symbol.upper(), symbol)

    if exchange.upper() == "NSE": return f"{yf_base_symbol}"
    elif exchange.upper() == "BSE":
        if not yf_base_symbol.endswith(".NS") and not yf_base_symbol.endswith(".BO"):
            return f"{yf_base_symbol}.BO"
        return yf_base_symbol
    return yf_base_symbol

@st.cache_data(ttl=30)
def get_live_stock_price_yf(symbol: str, exchange: str = "NSE"):
    yf_symbol = get_yfinance_symbol(symbol, exchange)
    print(f"Attempting yfinance live price for: {yf_symbol}")
    try:
        ticker = yf.Ticker(yf_symbol)
        live_price = ticker.info.get('regularMarketPrice')
        if live_price is None:
            live_price = ticker.info.get('currentPrice')
        if live_price is None:
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

@st.cache_data(ttl=15 * 60)
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
@st.cache_data(ttl=5 * 60)
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
            return [{
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

# ====================================================================
# --- NEW: Trading Strategy Engine and Decision Making ---
# ====================================================================

def generate_trading_signal(stock_data: pd.DataFrame, news_sentiment: str):
    """
    Generates a trading signal (BUY/SELL/HOLD) based on technical indicators and news sentiment.

    Args:
        stock_data (pd.DataFrame): DataFrame with historical OHLCV data.
        news_sentiment (str): Sentiment derived from the latest news ('positive', 'negative', 'neutral').

    Returns:
        dict: Contains the recommended action, confidence, and reasons.
    """
    if stock_data.empty or len(stock_data) < 20: # Need enough data for indicators
        return {
            "recommended_action": "HOLD",
            "confidence": 0.3,
            "reason": "Insufficient historical data for technical analysis.",
            "details": {}
        }

    # --- 1. Calculate Technical Indicators using pandas_ta ---
    # Ensure the DataFrame has the correct column names (Open, High, Low, Close, Volume)
    # pandas_ta adds columns directly to the DataFrame if append=True
    # We create a copy to avoid modifying the cached dataframe directly, if it was mutable.
    df = stock_data.copy()

    # SMA/EMA Crossover
    df.ta.sma(length=20, append=True) # Short-term SMA (e.g., 20 periods)
    df.ta.sma(length=50, append=True) # Long-term SMA (e.g., 50 periods)
    df.ta.ema(length=20, append=True) # Short-term EMA
    df.ta.ema(length=50, append=True) # Long-term EMA

    # RSI
    df.ta.rsi(append=True)

    # MACD
    df.ta.macd(append=True) # Default periods: (12, 26, 9)

    # Bollinger Bands
    df.ta.bbands(append=True) # Default periods: (20, 2.0) for standard deviations

    # Get the latest values for decision making
    last_close = df['Close'].iloc[-1]
    prev_close = df['Close'].iloc[-2]

    # Technical Indicators Signals
    technical_signals = {
        "buy_signals": 0,
        "sell_signals": 0,
        "neutral_signals": 0,
        "reasons": []
    }

    # --- SMA/EMA Crossover (Using latest available SMA/EMA values) ---
    sma_20 = df['SMA_20'].iloc[-1]
    sma_50 = df['SMA_50'].iloc[-1]
    prev_sma_20 = df['SMA_20'].iloc[-2]
    prev_sma_50 = df['SMA_50'].iloc[-2]

    ema_20 = df['EMA_20'].iloc[-1]
    ema_50 = df['EMA_50'].iloc[-1]
    prev_ema_20 = df['EMA_20'].iloc[-2]
    prev_ema_50 = df['EMA_50'].iloc[-2]

    # Simple Moving Average Crossover (20-period crossing above 50-period)
    if sma_20 > sma_50 and prev_sma_20 <= prev_sma_50: # Golden Cross (Buy signal)
        technical_signals["buy_signals"] += 1
        technical_signals["reasons"].append("SMA Crossover (20-day > 50-day)")
    elif sma_20 < sma_50 and prev_sma_20 >= prev_sma_50: # Death Cross (Sell signal)
        technical_signals["sell_signals"] += 1
        technical_signals["reasons"].append("SMA Crossover (20-day < 50-day)")
    else:
        technical_signals["neutral_signals"] += 1
        technical_signals["reasons"].append("SMA: Neutral")

    # Exponential Moving Average Crossover (similar logic)
    if ema_20 > ema_50 and prev_ema_20 <= prev_ema_50: # Golden Cross (Buy signal)
        technical_signals["buy_signals"] += 1
        technical_signals["reasons"].append("EMA Crossover (20-day > 50-day)")
    elif ema_20 < ema_50 and prev_ema_20 >= prev_ema_50: # Death Cross (Sell signal)
        technical_signals["sell_signals"] += 1
        technical_signals["reasons"].append("EMA Crossover (20-day < 50-day)")
    else:
        technical_signals["neutral_signals"] += 1
        technical_signals["reasons"].append("EMA: Neutral")


    # --- RSI ---
    rsi = df['RSI_14'].iloc[-1] # Default RSI period is 14
    if rsi < 30: # Oversold
        technical_signals["buy_signals"] += 1
        technical_signals["reasons"].append(f"RSI ({rsi:.2f}): Oversold (<30)")
    elif rsi > 70: # Overbought
        technical_signals["sell_signals"] += 1
        technical_signals["reasons"].append(f"RSI ({rsi:.2f}): Overbought (>70)")
    else:
        technical_signals["neutral_signals"] += 1
        technical_signals["reasons"].append(f"RSI ({rsi:.2f}): Neutral")

    # --- MACD ---
# --- NEW: Add MACD Chart ---
    st.markdown("### Moving Average Convergence Divergence (MACD)")
    df_plot_macd = stock_data.copy()

    # Debugging: Print the length of the DataFrame before MACD calculation
    print(f"DEBUG: df_plot_macd length BEFORE MACD calculation: {len(df_plot_macd)}")

    # Calculate MACD. Ensure this line runs and successfully adds the columns.
    df_plot_macd.ta.macd(append=True)

    # Debugging: Print all columns of the DataFrame AFTER MACD calculation
    print(f"DEBUG: df_plot_macd columns AFTER MACD calculation: {df_plot_macd.columns.tolist()}")

    # Check if MACD columns exist before attempting to plot
    macd_line_col = 'MACD_12_26_9'
    signal_line_col = 'MACDS_12_26_9'
    histogram_col = 'MACDH_12_26_9'

    # THIS IS THE CRITICAL CHANGE YOU NEED TO HAVE IN YOUR FILE
    if all(col in df_plot_macd.columns for col in [macd_line_col, signal_line_col, histogram_col]):
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df_plot_macd.index, y=df_plot_macd[macd_line_col], mode='lines', name='MACD Line', line=dict(color='blue')))
        fig_macd.add_trace(go.Scatter(x=df_plot_macd.index, y=df_plot_macd[signal_line_col], mode='lines', name='Signal Line', line=dict(color='orange')))
        fig_macd.add_trace(go.Bar(x=df_plot_macd.index, y=df_plot_macd[histogram_col], name='Histogram', marker_color=['green' if val >= 0 else 'red' for val in df_plot_macd[histogram_col]]))
        fig_macd.update_layout(
            xaxis_title="Date",
            yaxis_title="Value",
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(x=0, y=0.99, xanchor='left', yanchor='top')
        )
        st.plotly_chart(fig_macd, use_container_width=True)
    else:
        st.info("Not enough data or MACD calculation failed. Cannot plot MACD. (Requires at least 26 data points)")
        st.error(f"MACD calculation failed. Dataframe length: {len(df_plot_macd)}. Available columns: {df_plot_macd.columns.tolist()}")

    # --- Bollinger Bands ---
    bb_upper = df['BBL_20_2.0'].iloc[-1]
    bb_lower = df['BBU_20_2.0'].iloc[-1]

    if last_close < bb_lower: # Price touches or goes below lower band (often a buy signal)
        technical_signals["buy_signals"] += 1
        technical_signals["reasons"].append("Bollinger Bands: Price at Lower Band (oversold)")
    elif last_close > bb_upper: # Price touches or goes above upper band (often a sell signal)
        technical_signals["sell_signals"] += 1
        technical_signals["reasons"].append("Bollinger Bands: Price at Upper Band (overbought)")
    else:
        technical_signals["neutral_signals"] += 1
        technical_signals["reasons"].append("Bollinger Bands: Price within Bands (neutral)")

    # --- 2. Combine Technical and News Signals ---
    # Assign scores: +1 for buy, -1 for sell, 0 for neutral
    total_score = 0
    decision_reasons = []

    # Technical Score
    total_score += technical_signals["buy_signals"]
    total_score -= technical_signals["sell_signals"]
    decision_reasons.extend(technical_signals["reasons"])

    # News Sentiment Score
    news_weight = 2 # Give news a higher weight for immediate impact
    if news_sentiment == "positive":
        total_score += news_weight
        decision_reasons.append("Positive News Sentiment")
    elif news_sentiment == "negative":
        total_score -= news_weight
        decision_reasons.append("Negative News Sentiment")
    else:
        decision_reasons.append("Neutral News Sentiment")

    # --- 3. Generate Overall Decision ---
    recommended_action = "HOLD"
    confidence = 0.5 # Default confidence

    if total_score > 0:
        recommended_action = "BUY"
        confidence = min(1.0, 0.5 + (total_score / 10)) # Scale confidence based on score
    elif total_score < 0:
        recommended_action = "SELL/SHORT"
        confidence = min(1.0, 0.5 + (abs(total_score) / 10)) # Scale confidence based on score
    else:
        recommended_action = "HOLD"
        confidence = round(0.4 + np.random.rand() * 0.2, 2) # Random small confidence for HOLD

    # Placeholder for Stop Loss/Take Profit (these would ideally be dynamically calculated
    # based on volatility or average true range, not just random as in map_news_to_action)
    stop_loss = round(last_close * (1 - (confidence * 0.02 + 0.01)), 2) # Example: 1-3% below current price
    take_profit = round(last_close * (1 + (confidence * 0.03 + 0.02)), 2) # Example: 2-5% above current price

    # Ensure stop_loss is always lower than take_profit and current price for sensible values
    if recommended_action == "BUY":
        stop_loss = round(last_close * (1 - (confidence * 0.02 + 0.005)), 2)
        take_profit = round(last_close * (1 + (confidence * 0.03 + 0.01)), 2)
    elif recommended_action == "SELL/SHORT":
        stop_loss = round(last_close * (1 + (confidence * 0.02 + 0.005)), 2) # For short, stop loss is higher
        take_profit = round(last_close * (1 - (confidence * 0.03 + 0.01)), 2) # For short, take profit is lower
    else: # HOLD
        stop_loss = 0.00 # Not applicable for hold
        take_profit = 0.00 # Not applicable for hold


    return {
        "recommended_action": recommended_action,
        "confidence": round(confidence, 2),
        "reason": "; ".join(technical_signals["reasons"]),
        "details": {
            "technical_signals_count": technical_signals,
            "news_sentiment": news_sentiment,
            "total_score": total_score,
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
    }

# ====================================================================
# --- Streamlit UI Components (Updated to display new bot decision) ---
# ====================================================================

st.header(f"📈 Detailed Dashboard: {CURRENT_STOCK}")
st.write(f"Comprehensive insights for {CURRENT_STOCK} on BSE/NSE.")

st_autorefresh(interval=30 * 1000, key=f"data_refresh_{CURRENT_STOCK}")

# Display BSE and NSE prices (fetched directly here from yfinance)
st.markdown("---")
st.subheader("Current Market Prices")

price_placeholder = st.empty()

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

    ist_timezone = pytz.timezone('Asia/Kolkata')
    current_ist_time = datetime.now(ist_timezone)
    formatted_time = current_ist_time.strftime('%Y-%m-%d %H:%M:%S IST')
    st.markdown(f"<p style='text-align: right; font-size: 0.8em; color: gray;'>Last updated: {formatted_time}</p>", unsafe_allow_html=True)


st.subheader("Select Timeframe:")
timeframe_options = ["5m", "1d", "1w", "1m", "1y"]
selected_timeframe = st.radio(
    "Timeframe",
    timeframe_options,
    index=timeframe_options.index("1y"),
    horizontal=True,
    label_visibility="collapsed"
)

stock_data = get_historical_ohlc_yf(CURRENT_STOCK, selected_timeframe, "NSE")

# --- Graphs Section (Stacked Vertically) ---
st.markdown("---")
st.subheader(f"Price Charts for {CURRENT_STOCK}")

if not stock_data.empty:
    # Candlestick Chart
    st.markdown("### Candlestick Chart")
    fig_candlestick = go.Figure(data=[go.Candlestick(
        x=stock_data.index,
        open=stock_data['Open'],
        high=stock_data['High'],
        low=stock_data['Low'],
        close=stock_data['Close'],
        increasing_line_color='green',
        decreasing_line_color='red'
    )])
    # --- NEW: Add SMA/EMA to Candlestick chart if enough data ---
    if 'SMA_20' in stock_data.columns and 'SMA_50' in stock_data.columns:
        fig_candlestick.add_trace(go.Scatter(x=stock_data.index, y=stock_data['SMA_20'], mode='lines', name='SMA 20', line=dict(color='blue', width=1)))
        fig_candlestick.add_trace(go.Scatter(x=stock_data.index, y=stock_data['SMA_50'], mode='lines', name='SMA 50', line=dict(color='orange', width=1)))
    # Add Bollinger Bands if enough data
    if 'BBL_20_2.0' in stock_data.columns and 'BBU_20_2.0' in stock_data.columns:
        fig_candlestick.add_trace(go.Scatter(x=stock_data.index, y=stock_data['BBL_20_2.0'], mode='lines', name='Lower BB', line=dict(color='purple', dash='dot', width=1)))
        fig_candlestick.add_trace(go.Scatter(x=stock_data.index, y=stock_data['BBM_20_2.0'], mode='lines', name='Middle BB', line=dict(color='gray', dash='dot', width=1)))
        fig_candlestick.add_trace(go.Scatter(x=stock_data.index, y=stock_data['BBU_20_2.0'], mode='lines', name='Upper BB', line=dict(color='purple', dash='dot', width=1)))


    fig_candlestick.update_layout(
        xaxis_rangeslider_visible=False,
        xaxis_title="Date",
        yaxis_title="Price (₹)",
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(x=0, y=0.99, xanchor='left', yanchor='top') # Adjust legend position
    )
    st.plotly_chart(fig_candlestick, use_container_width=True)

    # Normal Line Graph (Close Price)
    st.markdown("### Normal Line Graph (Close Price)")
    fig_line = go.Figure(data=go.Scatter(
        x=stock_data.index,
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

    # --- NEW: Add RSI Chart ---
    st.markdown("### Relative Strength Index (RSI)")
    # Calculate RSI (it's already calculated in generate_trading_signal but we need it for plotting here)
    # Re-calculate or pass the DataFrame with indicators
    df_plot_rsi = stock_data.copy()
    df_plot_rsi.ta.rsi(append=True)
    if 'RSI_14' in df_plot_rsi.columns:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df_plot_rsi.index, y=df_plot_rsi['RSI_14'], mode='lines', name='RSI', line=dict(color='purple')))
        fig_rsi.add_hline(y=70, annotation_text="Overbought (70)", line_dash="dash", line_color="red")
        fig_rsi.add_hline(y=30, annotation_text="Oversold (30)", line_dash="dash", line_color="green")
        fig_rsi.update_layout(
            xaxis_title="Date",
            yaxis_title="RSI Value",
            height=300,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_rsi, use_container_width=True)
    else:
        st.info("Not enough data to calculate RSI for plotting.")


    # --- NEW: Add MACD Chart ---
    st.markdown("### Moving Average Convergence Divergence (MACD)")
    df_plot_macd = stock_data.copy()
    df_plot_macd.ta.macd(append=True)
    if 'MACD_12_26_9' in df_plot_macd.columns:
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df_plot_macd.index, y=df_plot_macd['MACD_12_26_9'], mode='lines', name='MACD Line', line=dict(color='blue')))
        fig_macd.add_trace(go.Scatter(x=df_plot_macd.index, y=df_plot_macd['MACDS_12_26_9'], mode='lines', name='Signal Line', line=dict(color='orange')))
        fig_macd.add_trace(go.Bar(x=df_plot_macd.index, y=df_plot_macd['MACDH_12_26_9'], name='Histogram', marker_color=['green' if val >= 0 else 'red' for val in df_plot_macd['MACDH_12_26_9']]))
        fig_macd.update_layout(
            xaxis_title="Date",
            yaxis_title="Value",
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(x=0, y=0.99, xanchor='left', yanchor='top')
        )
        st.plotly_chart(fig_macd, use_container_width=True)
    else:
        st.info("Not enough data to calculate MACD for plotting.")


else:
    st.warning(f"No stock data available for {CURRENT_STOCK} for the selected timeframe. Check yfinance compatibility for this symbol.")


# --- News Feed Section (fetched directly and processed) ---
st.markdown("---")
st.subheader(f"Latest News for {CURRENT_STOCK}")

raw_articles = get_financial_news_api(f"{CURRENT_STOCK} stock")

processed_news = []
latest_news_sentiment = "neutral" # Initialize for the combined decision
if raw_articles:
    # Use sentiment of the most relevant (first) article for overall news impact
    latest_news_sentiment = analyze_sentiment(f"{raw_articles[0].get('title', '')} {raw_articles[0].get('content', '')}")

# --- Generate the overall trading signal after getting stock data and news sentiment ---
overall_trading_signal = generate_trading_signal(stock_data, latest_news_sentiment)


if not raw_articles:
    st.info(f"No news found for {CURRENT_STOCK}.")
else:
    ist_timezone = pytz.timezone('Asia/Kolkata')

    for i, news_item in enumerate(raw_articles):
        full_text = f"{news_item.get('title', '')} {news_item.get('content', '')}"

        ticker_identified = perform_ner(full_text, CURRENT_STOCK)
        sentiment = analyze_sentiment(full_text)
        action_data = map_news_to_action(sentiment) # This is news-specific action, not overall bot action

        published_utc_str = news_item.get("publishedAt", "N/A")
        published_ist_str = "N/A"
        if published_utc_str != "N/A":
            try:
                published_utc = datetime.strptime(published_utc_str, '%Y-%m-%dT%H:%M:%SZ')
                published_ist = published_utc.replace(tzinfo=pytz.utc).astimezone(ist_timezone)
                published_ist_str = published_ist.strftime('%Y-%m-%d %H:%M:%S IST')
            except ValueError:
                published_ist_str = f"Invalid Date Format: {published_utc_str}"


        processed_news_item = {
            "source": news_item["source"],
            "title": news_item["title"],
            "content": news_item["content"],
            "url": news_item["url"],
            "publishedAt": published_ist_str,
            "sentiment": sentiment,
            "event": news_item["event"],
            "recommended_action": action_data["recommended_action"],
            "confidence": action_data["confidence"]
        }
        processed_news.append(processed_news_item)

    news_col1, news_col2 = st.columns(2)
    for i, news in enumerate(processed_news):
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

# --- Trading Bot Signal Output (Updated to use overall_trading_signal) ---
st.markdown("---")
st.subheader("Trading Bot Signal (Decision Engine)")
st.write("This signal combines Technical Analysis and News Sentiment.")

st.markdown(f"""
<div style="background-color: #e0f2f7; padding: 1.5rem; border-radius: 0.75rem; margin-top: 1.5rem; box-shadow: 0 4px 8px rgba(0,0,0,0.15);">
    <h3 style="color: #007bff; text-align: center; margin-bottom: 1rem;">Overall Recommended Action for {CURRENT_STOCK}</h3>
    <p style="font-size: 2.5rem; font-weight: bold; text-align: center; margin-bottom: 0.5rem;
       color: {'#16a34a' if overall_trading_signal['recommended_action'] == 'BUY' else ('#dc2626' if overall_trading_signal['recommended_action'] == 'SELL/SHORT' else '#f59e0b')};">
        {overall_trading_signal['recommended_action']}
    </p>
    <p style="text-align: center; font-size: 1.1rem; color: #555;">
        Confidence: <span style="font-weight: bold;">{overall_trading_signal['confidence']:.2f}</span>
    </p>
    <p style="text-align: center; font-size: 0.9rem; color: #777;">
        Reason(s): {overall_trading_signal['reason']}
    </p>
    {"<p style='text-align: center; font-size: 0.9rem; color: #777;'>Stop Loss: ₹" + str(overall_trading_signal['details']['stop_loss']) + "</p>" if overall_trading_signal['recommended_action'] != 'HOLD' else ""}
    {"<p style='text-align: center; font-size: 0.9rem; color: #777;'>Take Profit: ₹" + str(overall_trading_signal['details']['take_profit']) + "</p>" if overall_trading_signal['recommended_action'] != 'HOLD' else ""}
</div>
""", unsafe_allow_html=True)


st.subheader("Decision Engine Details (Raw Output)")
st.code(json.dumps(overall_trading_signal, indent=2), language='json')