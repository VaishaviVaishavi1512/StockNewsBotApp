import numpy as np

def decide_strategy(data):
    """
    data: dict with keys:
      - 'price', 'volume', 'rsi', 'ema50', 'ema200', 'high20', 'sentiment' (score -1 to 1)
    """
    strategy = ""
    signal = "HOLD"
    confidence = 0.5
    reasons = []

    # Strategy 1: Mean Reversion
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

    # Strategy 2: Trend Following
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

    # Strategy 3: Breakout
    if data['price'] > data['high20'] and data['volume'] > data['avg_volume'] * 1.5:
        strategy = "Breakout"
        signal = "BUY"
        confidence = 0.8
        reasons.append("Breakout above 20-day high with high volume")

    # Strategy 4: Sentiment Based
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