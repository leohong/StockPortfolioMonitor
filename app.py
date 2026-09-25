import streamlit as st

from src.logging_config import configure_logging
from src.ui import stock_detail

st.set_page_config(page_title="台股技術分析儀表板", layout="wide")
configure_logging()
st.navigation([st.Page(stock_detail, title="個股詳情", default=True)]).run()
