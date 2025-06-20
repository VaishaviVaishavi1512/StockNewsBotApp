import pandas as pd
import numpy as np
import ta

def generate_technical_signals(df):
    signal = "HOLD"

    # Calculate indicators
    df['EMA20'] = ta.trend.EMAIndicator(df['Close'], window=20).ema_indicator()
    df['EMA50'] = ta.trend.EMAIndicator(df['Close'], window=50).ema_indicator()
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()

    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()

    bb = ta.volatility.BollingerBands(df['Close'])
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()

    latest = df.iloc[-1]
    buy_signals = 0
    sell_signals = 0

    # EMA Crossover
    if latest['EMA20'] > latest['EMA50']:
        buy_signals += 1
    elif latest['EMA20'] < latest['EMA50']:
        sell_signals += 1

    # RSI
    if latest['RSI'] < 30:
        buy_signals += 1
    elif latest['RSI'] > 70:
        sell_signals += 1

    # MACD
    if latest['MACD'] > latest['MACD_signal']:
        buy_signals += 1
    elif latest['MACD'] < latest['MACD_signal']:
        sell_signals += 1

    # Bollinger Band
    if latest['Close'] < latest['bb_lower']:
        buy_signals += 1
    elif latest['Close'] > latest['bb_upper']:
        sell_signals += 1

    # Final Decision
    if buy_signals >= 2:
        signal = "BUY"
    elif sell_signals >= 2:
        signal = "SELL"

    return signal
