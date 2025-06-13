# pages/IRCTC.py
import streamlit as st
import pandas as pd
import numpy as np # Still useful for internal data manipulation if needed
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests # NEW: To make HTTP calls to your backend

# --- Backend API Configuration ---
# Make sure this matches the URL where your backend_app.py is running!
BACKEND_URL = "http://127.0.0.1:8000"

# --- Stock-Specific Configuration ---
CURRENT_STOCK = "IRCTC" # Hardcode for this page

# --- Functions to interact with your Backend API ---
@st.cache_data(ttl=5) # Cache live price for 5 seconds to avoid hitting backend too often
def get_live_price_from_backend(symbol):
    """Fetches live stock price from your FastAPI backend."""
    try:
        # Note: The backend endpoint /live_price/{symbol} expects only the symbol now
        response = requests.get(f"{BACKEND_URL}/live_price/{symbol}")
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        return data['price']
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to backend for live price: {e}. Is your backend running at {BACKEND_URL}?")
        return None
    except Exception as e:
        st.error(f"Failed to fetch live price for {symbol}: {e}")
        return None

@st.cache_data(ttl=300) # Cache historical data for 5 minutes (300 seconds)
def get_historical_ohlc_from_backend(symbol, timeframe, exchange="NSE"): # 'exchange' might be used by backend, pass it
    """Fetches historical OHLC data from your FastAPI backend."""
    try:
        # Your backend's /historical_data endpoint expects a POST request with JSON payload
        payload = {"symbol": symbol, "timeframe": timeframe, "exchange": exchange}
        response = requests.post(f"{BACKEND_URL}/historical_data", json=payload)
        response.raise_for_status()
        data = response.json()
        
        if not data: # Check if data is empty (e.g., API returned no results)
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df['Date'] = pd.to_datetime(df['Date']) # Convert 'Date' column back to datetime objects
        df = df.set_index('Date') # Set Date as index for plotting consistency
        df = df.sort_index() # Ensure chronological order

        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to backend for historical data: {e}. Is your backend running at {BACKEND_URL}?")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to fetch historical data for {symbol} ({timeframe}): {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60) # Cache news and analysis for 1 minute (60 seconds)
def get_news_and_analysis_from_backend(query):
    """Fetches news and analysis from your FastAPI backend."""
    try:
        # Your backend's /news_analysis endpoint expects a POST request with JSON payload
        payload = {"query": query}
        response = requests.post(f"{BACKEND_URL}/news_analysis", json=payload)
        response.raise_for_status()
        return response.json() # This should return {'news': [...], 'trading_signal': {...}}
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to backend for news: {e}. Is your backend running at {BACKEND_URL}?")
        return {"news": [], "trading_signal": {
            "ticker": query, "sentiment": "N/A", "event": "N/A",
            "confidence": 0.0, "recommended_action": "HOLD", "stop_loss": 0.0, "take_profit": 0.0
        }}
    except Exception as e:
        st.error(f"Failed to fetch news and analysis for {query}: {e}")
        return {"news": [], "trading_signal": {
            "ticker": query, "sentiment": "N/A", "event": "N/A",
            "confidence": 0.0, "recommended_action": "HOLD", "stop_loss": 0.0, "take_profit": 0.0
        }}

# --- Streamlit UI Components ---

st.header(f"📈 Detailed Dashboard: {CURRENT_STOCK}")
st.write(f"Comprehensive insights for {CURRENT_STOCK} on BSE/NSE.")

# Display BSE and NSE prices (fetched from backend)
st.markdown("---")
st.subheader("Current Market Prices")

# Fetch both BSE and NSE prices from backend (Alpha Vantage usually gives one price per symbol)
# For demo, we'll try to fetch for "IRCTC" and assume it might get a valid price.
# In a real app, you might need to query different symbols for BSE vs NSE specifically,
# like "IRCTC.BSE" and "IRCTC.NSE" if supported by your API.
bse_price = get_live_price_from_backend(CURRENT_STOCK) # Assuming AV provides for "IRCTC" generically
nse_price = get_live_price_from_backend(CURRENT_STOCK) # For demo, we use the same call for NSE, in real use, adjust symbol if needed

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
    st.info("Attempting to fetch live prices from backend...") # Message if prices are None

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

# Generate stock data based on selection (fetched from backend)
stock_data = get_historical_ohlc_from_backend(CURRENT_STOCK, selected_timeframe, "NSE") # Assume NSE for graphs

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
    st.warning(f"No stock data available for {CURRENT_STOCK} for the selected timeframe from the backend. Check backend logs for API errors or rate limits.")


# --- News Feed Section (fetched from backend and processed) ---
st.markdown("---")
st.subheader(f"Latest News for {CURRENT_STOCK}")

news_analysis_results = get_news_and_analysis_from_backend(CURRENT_STOCK)
news_articles = news_analysis_results["news"]
latest_trading_signal = news_analysis_results["trading_signal"]

news_col1, news_col2 = st.columns(2) # Keeping news in columns for better readability

if not news_articles:
    st.info(f"No news found for {CURRENT_STOCK} from the backend for the last 30 days. This might be due to API limits or no recent relevant news.")
else:
    for i, news in enumerate(news_articles):
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
st.write("This structured JSON output would be generated by your backend and sent to your trading bot API.")
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
