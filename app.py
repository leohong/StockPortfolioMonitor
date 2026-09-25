import streamlit as st

from src.logging_config import configure_logging
from src.ui import application

st.set_page_config(page_title="台股技術分析儀表板", layout="wide")
configure_logging()
application()
