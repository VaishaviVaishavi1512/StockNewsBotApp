# pages/IRCTC.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import yfinance as yf
import os

# --- Strategy Engine ---
def decide_strategy(data):
    strategy = ""
    signal = "HOLD"
    confidence = 0.5
    reasons = []

    if data['rsi'] < 30:
        strategy = "Mean Reversion"
        signal = "BUY"
        confidence = 0.75
        reasons.append(f"RSI is very low ({data['rsi']}) → Oversold")
    elif data['rsi'] > 70:
        strategy = "Mean Reversion"
        signal = "SELL"
        confidence = 0.75
        reasons.append(f"RSI is high ({data['rsi']}) → Overbought")

    elif data['ema50'] > data['ema200']:
        strategy = "Trend Following"
        signal = "BUY"
        confidence = 0.7
        reasons.append("50 EMA > 200 EMA → Bullish trend")
    elif data['ema50'] < data['ema200']:
        strategy = "Trend Following"
        signal = "SELL"
        confidence = 0.7
        reasons.append("50 EMA < 200 EMA → Bearish trend")

    if data['price'] > data['high20'] and data['volume'] > data['avg_volume'] * 1.5:
        strategy = "Breakout"
        signal = "BUY"
        confidence = 0.8
        reasons.append("Breakout above 20-day high with high volume")

    if data['sentiment'] > 0.5:
        signal = "BUY"
        confidence = max(confidence, 0.8)
        reasons.append("Very positive news sentiment")
    elif data['sentiment'] < -0.5:
        signal = "SELL"
        confidence = max(confidence, 0.8)
        reasons.append("Very negative news sentiment")

    return {
        "strategy": strategy or "Neutral",
        "signal": signal,
        "confidence": round(confidence, 2),
        "reasons": reasons
    }

# --- RSI Calculation ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# --- Stock-Specific Configuration ---
CURRENT_STOCK = "IRCTC"

# --- Streamlit Content ---
st.header(f"📈 Detailed Dashboard: {CURRENT_STOCK}")
st.write(f"Comprehensive insights for {CURRENT_STOCK} on BSE/NSE.")

bse_price = yf.Ticker(f"{CURRENT_STOCK}.BO").info.get('regularMarketPrice', None)
nse_price = yf.Ticker(f"{CURRENT_STOCK}.NS").info.get('regularMarketPrice', None)

st.subheader("Current Market Prices")
if bse_price and nse_price:
    st.success(f"BSE: ₹{bse_price:.2f} | NSE: ₹{nse_price:.2f}")
else:
    st.warning("Price data not available.")

# --- Historical Data Fetch ---
stock_data = yf.Ticker(f"{CURRENT_STOCK}.NS").history(period="6mo")

# --- Graphs ---
st.subheader("Price Charts")
fig = go.Figure(data=[go.Candlestick(x=stock_data.index,
                                     open=stock_data['Open'],
                                     high=stock_data['High'],
                                     low=stock_data['Low'],
                                     close=stock_data['Close'])])
st.plotly_chart(fig, use_container_width=True)

# --- Technical Indicators ---
rsi_14 = calculate_rsi(stock_data['Close'], 14)
ema_50 = stock_data['Close'].ewm(span=50).mean().iloc[-1]
ema_200 = stock_data['Close'].ewm(span=200).mean().iloc[-1]
high_20 = stock_data['High'].rolling(window=20).max().iloc[-1]
avg_volume = stock_data['Volume'].rolling(20).mean().iloc[-1]
latest_price = stock_data['Close'].iloc[-1]
latest_volume = stock_data['Volume'].iloc[-1]

# --- Placeholder Sentiment ---
sentiment_score = 0.6  # Simulate from earlier NLP analysis

# --- Strategy Engine ---
strategy_input = {
    "price": latest_price,
    "volume": latest_volume,
    "avg_volume": avg_volume,
    "rsi": rsi_14,
    "ema50": ema_50,
    "ema200": ema_200,
    "high20": high_20,
    "sentiment": sentiment_score
}

decision = decide_strategy(strategy_input)

st.subheader("🧠 Strategy Decision Engine")
st.write(f"**Strategy Used:** {decision['strategy']}")
st.write(f"**Signal:** `{decision['signal']}` (Confidence: {int(decision['confidence'] * 100)}%)")
st.markdown("**Reasons:**")
for r in decision['reasons']:
    st.markdown(f"- {r}")
