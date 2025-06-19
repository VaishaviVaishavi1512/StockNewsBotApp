# live_price_monitor.py
import streamlit as st
import yfinance as yf
import time

# Mapping your stock names to NSE tickers
stock_map = {
    "Bharat Electronics": "BEL.NS",
    "Tata Motors": "TATAMOTORS.NS",
    "SBI": "SBIN.NS",
    "IRCTC": "IRCTC.NS",
    "IndiGo": "INDIGO.NS"
}

st.set_page_config(page_title="📈 Live Stock Monitor", layout="centered")
st.title("🔁 Live Stock Price Monitoring (5 Indian Stocks)")

selected_stock = st.selectbox("Choose a stock to monitor", list(stock_map.keys()))
ticker = yf.Ticker(stock_map[selected_stock])

refresh_rate = st.slider("Refresh interval (seconds)", 3, 30, 5)

if "prev_price" not in st.session_state:
    st.session_state.prev_price = 0

price_placeholder = st.empty()
change_placeholder = st.empty()

while True:
    data = ticker.history(period="1d", interval="1m")
    if data.empty:
        st.warning("No data received.")
        break

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

    time.sleep(refresh_rate)
    st.experimental_rerun()