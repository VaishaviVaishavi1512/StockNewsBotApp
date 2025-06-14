import streamlit as st
import yfinance as yf # Added for robustness
import plotly.graph_objects as go # Added for robustness
import pandas as pd # Added for robustness
import numpy as np # Added for robustness

st.set_page_config(
    page_title="Stock News Bot",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.title("Welcome to the Stock News Bot 📈")
st.markdown("""
    Get real-time stock prices, historical data, and AI-powered news analysis for informed trading decisions.
    Use the sidebar to navigate to specific stock dashboards.
    
    **Note:** Stock prices are delayed as per yfinance/Yahoo Finance. News analysis is simulated.
""")

st.image("https://placehold.co/600x300/F0F8FF/000000?text=Stock+Market+Overview", caption="Live Market Overview (Simulated)", use_column_width=True)

st.subheader("How it Works:")
st.markdown("""
1.  **Select a Stock:** Choose from the available Indian stocks in the sidebar.
2.  **View Dashboard:** See current prices, historical charts (candlestick and line graphs).
3.  **Get News Analysis:** Read the latest financial news related to the selected stock, with simulated sentiment and trading action recommendations.
""")

st.subheader("Disclaimer:")
st.info("""
This application provides simulated trading signals and analysis for educational and demonstration purposes only. 
It relies on data from external APIs (yfinance for stock data, NewsAPI.org for news). 
Real-time stock data from yfinance may be delayed. 
The AI-powered sentiment analysis and trading recommendations are purely illustrative and should **NOT** be used for actual financial decisions. 
Always consult with a qualified financial advisor before making any investment decisions.
""")

# You can add more general information or summary here if needed
