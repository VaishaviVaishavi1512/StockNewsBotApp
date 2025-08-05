from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np
import ta
from collections import Counter

app = FastAPI()

class StockInput(BaseModel):
    stock: str  # right now we’ll only handle IRCTC

# Simple data fetcher
def fetch_stock_data(stock_symbol):
    yf_symbol = stock_symbol.upper() + ".NS"  # e.g., IRCTC -> IRCTC.NS
    ticker = yf.Ticker(yf_symbol)
    df = ticker.history(period="1y", interval="1d")
    df = df.dropna()
    return df

# Simple mock news sentiment (for now; FinBERT can be added later)
def mock_news_signal():
    return {
        "recommended_action": np.random.choice(["BUY", "SELL", "HOLD"]),
        "confidence": round(0.8 + np.random.rand() * 0.1, 2),
        "stop_loss": round(2.5 + np.random.rand(), 2),
        "take_profit": round(5 + np.random.rand() * 2, 2)
    }

def decide(stock_symbol):
    df = fetch_stock_data(stock_symbol)
    close = df["Close"]

    signals = []

    # 1. EMA
    ema20 = ta.trend.ema_indicator(close, window=20).fillna(0)
    ema50 = ta.trend.ema_indicator(close, window=50).fillna(0)
    signals.append("BUY" if ema20.iloc[-1] > ema50.iloc[-1] else "SELL")

    # 2. SMA
    sma20 = ta.trend.sma_indicator(close, window=20).fillna(0)
    sma50 = ta.trend.sma_indicator(close, window=50).fillna(0)
    signals.append("BUY" if sma20.iloc[-1] > sma50.iloc[-1] else "SELL")

    # 3. RSI
    rsi = ta.momentum.RSIIndicator(close, window=14).rsi().fillna(50)
    signals.append("BUY" if rsi.iloc[-1] < 30 else "SELL" if rsi.iloc[-1] > 70 else "HOLD")

    # 4. MACD
    macd_diff = ta.trend.macd_diff(close).fillna(0)
    signals.append("BUY" if macd_diff.iloc[-1] > 0 else "SELL")

    # 5. Bollinger Bands
    bb = ta.volatility.BollingerBands(close, window=20)
    lower = bb.bollinger_lband().iloc[-1]
    upper = bb.bollinger_hband().iloc[-1]
    price = close.iloc[-1]
    if price < lower:
        signals.append("BUY")
    elif price > upper:
        signals.append("SELL")
    else:
        signals.append("HOLD")

    # 6. News Sentiment (mocked here)
    news_signal = mock_news_signal()
    signals.append(news_signal["recommended_action"])

    # Final vote
    final = Counter(signals).most_common(1)[0][0]

    return {
        "stock": stock_symbol.upper(),
        "signal": final,
        "strategy_votes": signals,
        "confidence": news_signal["confidence"],
        "stop_loss": news_signal["stop_loss"],
        "take_profit": news_signal["take_profit"]
    }

@app.post("/predict")
def predict(data: StockInput):
    result = decide(data.stock)
    return result
