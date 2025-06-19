import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import yfinance as yf
import time

CURRENT_STOCK = "IRCTC"
TICKER_NSE = "IRCTC.NS"
TICKER_BSE = "IRCTC.BO"

st.set_page_config(page_title="IRCTC Dashboard", layout="wide")

# -------------------------------
# LIVE NSE & BSE PRICES
# -------------------------------
st.title("📊 IRCTC Stock Dashboard")

st.subheader("🔎 Live Prices (BSE / NSE)")

try:
    bse_price = yf.Ticker(TICKER_BSE).info.get("regularMarketPrice")
    nse_price = yf.Ticker(TICKER_NSE).info.get("regularMarketPrice")
    st.markdown(f"""
    <div style='display: flex; gap: 2rem; font-size: 1.2rem;'>
        <span style='color: green;'>BSE: ₹{bse_price}</span>
        <span style='color: blue;'>NSE: ₹{nse_price}</span>
    </div>
    """, unsafe_allow_html=True)
except:
    st.warning("⚠ Could not fetch live prices.")

# -------------------------------
# LIVE PRICE MONITOR
# -------------------------------
st.subheader("🔁 Live Price Monitor")

refresh_rate = st.slider("Refresh Interval (sec)", 5, 30, 10)
ticker = yf.Ticker(TICKER_NSE)

if "prev_price" not in st.session_state:
    st.session_state.prev_price = 0

price_placeholder = st.empty()
change_placeholder = st.empty()

data = ticker.history(period="1d", interval="1m")
if not data.empty:
    current_price = data['Close'].iloc[-1]
    previous_price = st.session_state.prev_price
    st.session_state.prev_price = current_price

    pct_change = ((current_price - previous_price) / previous_price * 100) if previous_price != 0 else 0

    if pct_change > 0.2:
        price_placeholder.markdown(f"### 🟢 ₹{current_price:.2f}")
        change_placeholder.success(f"↑ {pct_change:.2f}%")
    elif pct_change < -0.2:
        price_placeholder.markdown(f"### 🔴 ₹{current_price:.2f}")
        change_placeholder.error(f"↓ {pct_change:.2f}%")
    else:
        price_placeholder.markdown(f"### ₹{current_price:.2f}")
        change_placeholder.info(f"↔ {pct_change:.2f}%")
else:
    st.warning("No live data available.")

# -------------------------------
# STOCK CHARTS (CANDLE + LINE)
# -------------------------------
st.markdown("---")
st.subheader("📈 Price Charts")

@st.cache_data(ttl=600)
def get_stock_data(ticker, tf):
    period_map = {'5m': '1d', '1d': '5d', '1w': '1mo', '1m': '3mo', '1y': '1y'}
    interval_map = {'5m': '5m', '1d': '60m', '1w': '1d', '1m': '1d', '1y': '1d'}
    return yf.Ticker(ticker).history(period=period_map[tf], interval=interval_map[tf])

timeframe = st.selectbox("Select Timeframe", ["5m", "1d", "1w", "1m", "1y"], index=4)
stock_data = get_stock_data(TICKER_NSE, timeframe)

if not stock_data.empty:
    # Candlestick
    st.markdown("### Candlestick Chart")
    fig = go.Figure(data=[go.Candlestick(
        x=stock_data.index,
        open=stock_data['Open'],
        high=stock_data['High'],
        low=stock_data['Low'],
        close=stock_data['Close'],
        increasing_line_color='green',
        decreasing_line_color='red'
    )])
    fig.update_layout(xaxis_title="Date", yaxis_title="Price (₹)", height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Line chart
    st.markdown("### Line Chart")
    fig2 = go.Figure(data=go.Scatter(
        x=stock_data.index,
        y=stock_data['Close'],
        mode='lines',
        line=dict(color='blue', width=2)
    ))
    fig2.update_layout(xaxis_title="Date", yaxis_title="Close Price (₹)", height=400)
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.warning("No chart data found.")

# -------------------------------
# NEWS + SENTIMENT + SIGNAL
# -------------------------------
st.markdown("---")
st.subheader("📰 Latest News & Signal")

# Mock News
news = {
    "title": "IRCTC stock stable amid market fluctuations",
    "content": "IRCTC maintains stability despite broader index movements.",
    "source": "Mock News",
    "url": "#",
    "sentiment": "neutral",
    "action": "HOLD"
}

st.markdown(f"""
**{news['title']}**  
{news['content']}  
Sentiment: *{news['sentiment'].upper()}*  
Recommended Action: **{news['action']}**  
[Read more]({news['url']})
""")

# -------------------------------
# BOT SIGNAL
# -------------------------------
st.markdown("---")
st.subheader("🤖 Trading Bot Signal")

st.code(f'''
{{
    "ticker": "IRCTC",
    "sentiment": "{news['sentiment']}",
    "recommended_action": "{news['action']}",
    "confidence": 0.70,
    "stop_loss": 3.5,
    "take_profit": 6.5
}}
''', language='json')
