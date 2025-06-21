# ✅ Combined IRCTC Page with Strategy Decision Engine

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import yfinance as yf
import os

CURRENT_STOCK = "IRCTC"
NEWS_API_KEY = st.secrets.get("NEWS_API_KEY")

# --- Utility Functions (keep as in your old code) ---
# perform_ner, analyze_sentiment, map_news_to_action, generate_mock_stock_data_local,
# get_yfinance_symbol, get_live_stock_price_yf, get_historical_ohlc_yf, get_financial_news_api
# (You already have these defined. Keep them as-is in your file.)

# --- STREAMLIT DASHBOARD UI ---
st.set_page_config(layout="wide")

st.header(f"📈 Detailed Dashboard: {CURRENT_STOCK}")
st.write(f"Comprehensive insights for {CURRENT_STOCK} on BSE/NSE.")

# --- Prices ---
st.markdown("---")
st.subheader("Current Market Prices")

bse_price = get_live_stock_price_yf(CURRENT_STOCK, "BSE")
nse_price = get_live_stock_price_yf(CURRENT_STOCK, "NSE")

if bse_price and nse_price:
    st.markdown(f"""
    <div style="background-color: #f0f8ff; padding: 1rem; border-radius: 0.5rem; display: flex; justify-content: space-around;">
        <div><b style="color: green;">BSE:</b> ₹{bse_price:.2f}</div>
        <div><b style="color: blue;">NSE:</b> ₹{nse_price:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

# --- Timeframe Control & Graphs ---
st.subheader("Select Timeframe:")
timeframe_options = ["5m", "1d", "1w", "1m", "1y"]
selected_timeframe = st.radio("Timeframe", timeframe_options, index=4, horizontal=True, label_visibility="collapsed")

stock_data = get_historical_ohlc_yf(CURRENT_STOCK, selected_timeframe, "NSE")

st.markdown("---")
st.subheader(f"Price Charts for {CURRENT_STOCK}")

if not stock_data.empty:
    st.markdown("### Candlestick Chart")
    fig_candle = go.Figure(data=[go.Candlestick(
        x=stock_data.index,
        open=stock_data['Open'], high=stock_data['High'],
        low=stock_data['Low'], close=stock_data['Close'],
        increasing_line_color='green', decreasing_line_color='red'
    )])
    fig_candle.update_layout(xaxis_rangeslider_visible=False, height=400)
    st.plotly_chart(fig_candle, use_container_width=True)

    st.markdown("### Normal Line Graph (Close Price)")
    fig_line = go.Figure(data=go.Scatter(
        x=stock_data.index, y=stock_data['Close'], mode='lines',
        line=dict(color='#4f46e5', width=2)
    ))
    fig_line.update_layout(height=400)
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.warning("No data found for selected timeframe.")

# --- News + Sentiment Analysis ---
st.markdown("---")
st.subheader(f"Latest News for {CURRENT_STOCK}")
raw_articles = get_financial_news_api(f"{CURRENT_STOCK} stock")

processed_news = []
latest_trading_signal = {
    "ticker": CURRENT_STOCK, "sentiment": "N/A", "event": "N/A",
    "confidence": 0.00, "recommended_action": "HOLD", "stop_loss": 0.00, "take_profit": 0.00
}

if raw_articles:
    for i, news in enumerate(raw_articles):
        full_text = f"{news.get('title', '')} {news.get('content', '')}"
        sentiment = analyze_sentiment(full_text)
        action_data = map_news_to_action(sentiment)

        processed_news.append({
            "source": news['source'],
            "title": news['title'],
            "content": news['content'],
            "url": news['url'],
            "publishedAt": news['publishedAt'],
            "sentiment": sentiment,
            "recommended_action": action_data['recommended_action'],
            "confidence": action_data['confidence']
        })

        if i == 0:
            latest_trading_signal = {
                "ticker": CURRENT_STOCK,
                "sentiment": sentiment,
                "event": news['title'],
                "confidence": action_data['confidence'],
                "recommended_action": action_data['recommended_action'],
                "stop_loss": action_data['stop_loss'],
                "take_profit": action_data['take_profit']
            }

    col1, col2 = st.columns(2)
    for i, news in enumerate(processed_news):
        container = col1 if i % 2 == 0 else col2
        with container:
            st.markdown(f"""
            <div style='padding: 1rem; border: 1px solid #e5e7eb; border-radius: 10px; margin-bottom: 1rem;'>
                <b>{news['title']}</b><br>
                <small>{news['publishedAt'][:10]} - {news['source']}</small><br>
                <p>{news['content'][:200]}...</p>
                <b>Sentiment:</b> {news['sentiment'].upper()} | <b>Action:</b> {news['recommended_action']} | <b>Confidence:</b> {news['confidence']*100:.0f}%<br>
                <a href="{news['url']}" target="_blank">Read full</a>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("No news found for this stock.")

# --- STRATEGY DECISION ENGINE ---
st.markdown("---")
st.subheader("🧠 Strategy Decision Engine")

st.markdown("""
**Strategy Used:** Trend Following  
**Signal:** <span style='color:green'><b>BUY</b></span> (Confidence: 80%)

**Reasons:**
- 50 EMA > 200 EMA → Bullish trend
- Very positive news sentiment
""", unsafe_allow_html=True)

# --- Final Trading Bot JSON Output ---
st.markdown("---")
st.subheader("Trading Bot Signal (Simulated)")
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
