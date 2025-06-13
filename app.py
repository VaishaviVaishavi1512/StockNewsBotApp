import streamlit as st
from datetime import datetime
import yfinance as yf

# ---------------------------
# Page Configuration
# ---------------------------
st.set_page_config(
    page_title="Trading Intelligence Dashboard",
    layout="wide",
    page_icon="📊"
)

# ---------------------------
# Custom CSS
# ---------------------------
st.markdown("""
    <style>
        .main-title {
            font-size: 42px;
            font-weight: 800;
            margin-bottom: 10px;
        }
        .subheader {
            font-size: 20px;
            color: #6c757d;
        }
        .stock-box {
            padding: 15px;
            border-radius: 12px;
            background-color: #f8f9fa;
            box-shadow: 0px 2px 10px rgba(0,0,0,0.05);
            text-align: center;
            transition: transform 0.2s ease;
        }
        .stock-box:hover {
            background-color: #e9ecef;
            transform: scale(1.03);
        }
        .stock-link {
            font-size: 18px;
            font-weight: 700;
            color: #2c7be5;
            text-decoration: none;
        }
        .stock-link:hover {
            text-decoration: underline;
        }
        .ticker-text {
            font-size: 14px;
            color: #555;
            margin-top: 4px;
        }
        .price-text {
            font-size: 16px;
            color: #000;
            margin-top: 6px;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Stock Data
# ---------------------------
stock_data = {
    "Bharat Electronics": {
        "page": "Bharat_Electronics",
        "ticker": "BEL.NS"
    },
    "Tata Motors": {
        "page": "Tata_Motors",
        "ticker": "TATAMOTORS.NS"
    },
    "IRCTC": {
        "page": "IRCTC",
        "ticker": "IRCTC.NS"
    },
    "IndiGo Airlines": {
        "page": "Indigo_Airlines",
        "ticker": "INDIGO.NS"
    },
    "SBI": {
        "page": "SBI",
        "ticker": "SBIN.NS"
    }
}

# ---------------------------
# Header
# ---------------------------
st.markdown('<div class="main-title">📊 Trading Intelligence Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="subheader">Focused Market Intelligence for 5 High-Value Stocks</div>', unsafe_allow_html=True)
st.markdown("---")

# ---------------------------
# Stock Cards
# ---------------------------
st.subheader("🧾 Tracked Equities")

cols = st.columns(5)

for col, (company, info) in zip(cols, stock_data.items()):
    ticker = info["ticker"]
    page = info["page"]

    # Fetch price using yfinance
    try:
        stock = yf.Ticker(ticker)
        price = stock.info['regularMarketPrice']
        price_text = f"₹{price:.2f}" if price else "N/A"
    except Exception:
        price_text = "N/A"

    with col:
        st.markdown(f"""
            <div class="stock-box">
                <a href="./{page}" class="stock-link">{company}</a>
                <div class="ticker-text">{ticker}</div>
                <div class="price-text">{price_text}</div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ---------------------------
# Info
# ---------------------------
st.info("Click on a stock above to view detailed dashboards including price charts, news sentiment, and trading signals.")
st.success("⚙️ Backend modules like NLP sentiment, action mapping, and live news scraping are under construction.")
st.markdown("---")
st.caption(f"© {datetime.now().year} | Built with ❤️ using Streamlit")
