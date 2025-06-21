# pages/IRCTC.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

# --- Constants ---
CURRENT_STOCK = "IRCTC"
NEWS_API_KEY = st.secrets.get("NEWS_API_KEY")

# --- NLP and Mapping ---
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
    pos = ["profit", "soar", "jump", "rises", "invest", "contract", "boosts", "growth", "strong", "improves", "expands", "dividend", "bullish", "exceeding expectations", "robust", "healthy", "gains", "partnership", "collaboration", "launch"]
    neg = ["loss", "headwinds", "rising fuel", "supply chain issues", "missed", "resigned", "downgrade", "decline", "fall", "struggle", "uncertainty", "volatility", "challenges"]
    neu = ["board approves", "plans", "announces", "decision", "discussions", "talks", "quarterly results"]
    score = 0
    txt = text.lower()
    for w in pos: score += txt.count(w)
    for w in neg: score -= txt.count(w)
    if score > 0: return "positive"
    elif score < 0: return "negative"
    else: return "neutral" if any(w in txt for w in neu) else "neutral"

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
    return {"recommended_action": action, "confidence": confidence, "stop_loss": stop_loss, "take_profit": take_profit}

# --- Finance Functions ---
def get_yf_symbol(stock, exchange):
    suffix = ".NS" if exchange == "NSE" else ".BO"
    return {
        "IRCTC": "IRCTC",
        "SBI": "SBIN",
        "TATA MOTORS": "TATAMOTORS",
        "BHARAT ELECTRONICS": "BEL",
        "INDIGO AIRLINES": "INDIGO"
    }.get(stock.upper(), stock) + suffix

@st.cache_data(ttl=30)
def get_live_price(stock, exchange):
    try:
        ticker = yf.Ticker(get_yf_symbol(stock, exchange))
        return ticker.info.get("regularMarketPrice") or ticker.history(period="1d", interval="1m")["Close"].iloc[-1]
    except:
        return np.round(np.random.uniform(980, 1020), 2)

@st.cache_data(ttl=600)
def get_ohlc(stock, timeframe, exchange="NSE"):
    symbol = get_yf_symbol(stock, exchange)
    period_map = {"5m": "1d", "1d": "5d", "1w": "1mo", "1m": "3mo", "1y": "1y"}
    interval_map = {"5m": "5m", "1d": "60m", "1w": "1d", "1m": "1d", "1y": "1d"}
    try:
        df = yf.Ticker(symbol).history(period=period_map[timeframe], interval=interval_map[timeframe])
        df.index.name = "Date"
        return df[["Open", "High", "Low", "Close", "Volume"]]
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_news(query):
    if not NEWS_API_KEY:
        return [{"source": "Mock", "title": "API Key Missing", "content": "Mock news...", "url": "#", "publishedAt": str(datetime.now())}]
    try:
        res = requests.get("https://newsapi.org/v2/everything", params={
            "q": query, "language": "en", "sortBy": "relevancy",
            "from": (datetime.now() - timedelta(days=15)).isoformat(),
            "apiKey": NEWS_API_KEY, "pageSize": 20
        }, timeout=10)
        data = res.json()
        return [{
            "source": a["source"]["name"],
            "title": a["title"],
            "content": a["description"] or "",
            "url": a["url"],
            "publishedAt": a["publishedAt"]
        } for a in data.get("articles", [])]
    except:
        return [{"source": "Error", "title": "Failed to fetch news", "content": "Fallback content", "url": "#", "publishedAt": str(datetime.now())}]

# --- UI Start ---
st.set_page_config(layout="wide")
st_autorefresh(interval=30000, key="refresh")

st.header(f"📈 {CURRENT_STOCK} Dashboard")

# Prices
nse_price = get_live_price(CURRENT_STOCK, "NSE")
bse_price = get_live_price(CURRENT_STOCK, "BSE")
st.subheader("Live Prices")
st.markdown(f"**NSE:** ₹{nse_price:.2f} &nbsp;&nbsp;|&nbsp;&nbsp; **BSE:** ₹{bse_price:.2f}")

# Timeframe
st.subheader("Select Timeframe")
tf = st.radio("Timeframe", ["5m", "1d", "1w", "1m", "1y"], horizontal=True, label_visibility="collapsed")
stock_data = get_ohlc(CURRENT_STOCK, tf)

# Charts
st.subheader("Candlestick Chart")
if not stock_data.empty:
    fig = go.Figure(data=[go.Candlestick(x=stock_data.index,
                                         open=stock_data["Open"],
                                         high=stock_data["High"],
                                         low=stock_data["Low"],
                                         close=stock_data["Close"])])
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Line Chart")
    st.line_chart(stock_data["Close"])
else:
    st.warning("No stock data available.")

# News
st.subheader("📢 News and Signals")
articles = get_news(CURRENT_STOCK + " stock")
latest_signal = {}
cols = st.columns(2)
for i, a in enumerate(articles):
    sentiment = analyze_sentiment(a["title"] + " " + a["content"])
    action = map_news_to_action(sentiment)
    if i == 0:
        latest_signal = {
            "ticker": CURRENT_STOCK,
            "sentiment": sentiment,
            "event": "News-based event",
            "confidence": action["confidence"],
            "recommended_action": action["recommended_action"],
            "stop_loss": action["stop_loss"],
            "take_profit": action["take_profit"]
        }
    html = f"""
    <div style="padding:1rem;border:1px solid #eee;border-radius:8px;margin-bottom:1rem">
        <b>{a['title']}</b><br>
        <small>{a['publishedAt'][:10]} | {a['source']}</small><br>
        <i>{sentiment.upper()} → {action['recommended_action']}</i><br>
        <a href="{a['url']}" target="_blank">Read More</a>
    </div>
    """
    cols[i % 2].markdown(html, unsafe_allow_html=True)

# Trading Bot Output
st.subheader("🤖 Trading Bot Signal Output")
st.code(f"""
{{
  "ticker": "{latest_signal.get("ticker", "N/A")}",
  "sentiment": "{latest_signal.get("sentiment", "N/A")}",
  "event": "{latest_signal.get("event", "N/A")}",
  "confidence": {latest_signal.get("confidence", 0.0)},
  "recommended_action": "{latest_signal.get("recommended_action", "HOLD")}",
  "stop_loss": {latest_signal.get("stop_loss", 0.0)},
  "take_profit": {latest_signal.get("take_profit", 0.0)}
}}
""", language="json")

# Strategy Decision Engine
st.subheader("🧠 Strategy Decision Engine")
if not stock_data.empty:
    ema20 = stock_data["Close"].ewm(span=20).mean()
    ema50 = stock_data["Close"].ewm(span=50).mean()
    ema_sig = "BUY" if ema20.iloc[-1] > ema50.iloc[-1] else "SELL" if ema20.iloc[-1] < ema50.iloc[-1] else "HOLD"
    volatility = np.std(stock_data["Close"].pct_change().dropna())
    vol_sig = "HIGH RISK" if volatility > 0.02 else "STABLE"
    st.markdown(f"""
    <div style="background:#e6ffed;padding:1rem;border-radius:8px">
        <h4>📊 EMA Signal</h4>
        20 EMA: ₹{ema20.iloc[-1]:.2f} | 50 EMA: ₹{ema50.iloc[-1]:.2f}<br>
        <b>Signal:</b> {ema_sig}
    </div><br>
    <div style="background:#fff7ed;padding:1rem;border-radius:8px">
        <h4>⚠️ Volatility</h4>
        Std Dev: {volatility:.4f}<br>
        <b>Condition:</b> {vol_sig}
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("Cannot compute strategy signals without price data.")
