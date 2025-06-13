import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="BEL Candlestick", layout="wide")
st.title("📈 BEL.NS Candlestick Chart - Past 1 Year")

# Dates
end = datetime.today()
start = end - timedelta(days=365)

# Fetch data
df = yf.download("BEL.NS", start=start, end=end)

if df.empty:
    st.error("❌ Could not fetch stock data.")
else:
    df.reset_index(inplace=True)

    # Candlestick chart using plotly
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df['Date'],
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                increasing_line_color='green',
                decreasing_line_color='red'
            )
        ]
    )

    fig.update_layout(
        title="BEL.NS - 1 Year Candlestick Chart",
        xaxis_title="Date",
        yaxis_title="Price (₹)",
        xaxis_rangeslider_visible=False,
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)
