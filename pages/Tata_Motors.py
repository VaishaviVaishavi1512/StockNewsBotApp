import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# Page Setup
st.set_page_config(page_title="Tata Motors Candlestick", layout="wide")

# Title
st.title("📉 Candlestick Chart - Tata Motors")

# Fetching last 30 days of stock data
ticker = "TATAMOTORS.NS"
end_date = datetime.today()
start_date = end_date - timedelta(days=30)

df = yf.download(ticker, start=start_date, end=end_date)

if df.empty:
    st.error("No data found for Tata Motors.")
else:
    # Reset index to get 'Date' column for x-axis
    df.reset_index(inplace=True)

    st.subheader("Tata Motors - Last 30 Days")

    fig = go.Figure(data=[
        go.Candlestick(
            x=df['Date'],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            increasing_line_color='green',
            decreasing_line_color='red'
        )
    ])

    fig.update_layout(
        xaxis_title='Date',
        yaxis_title='Price',
        xaxis_rangeslider_visible=False,
        template='plotly_white',
        width=1000,
        height=500
    )

    st.plotly_chart(fig)

    # Optional detailed data
    with st.expander("📊 Detailed Stock Data"):
        st.dataframe(df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']])
