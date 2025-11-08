import streamlit as st
from pages import home, analytics, settings, task
from datetime import datetime
from utils.helpers import retrieve_and_plot_shop_analysis

# Configure page settings
st.set_page_config(
    page_title="Modular Streamlit Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar Navigation
st.sidebar.title("📚 Navigation")
PAGES = {
    "🏠 Home": home,
    "📈 Analytics": analytics,
    "⚙️ Settings": settings,
    "tasks": task
}

selection = st.sidebar.radio("Go to", list(PAGES.keys()))

retrieve_and_plot_shop_analysis(
    start_time=datetime(2025, 10, 1), end_time=(datetime(2025, 10, 31))
)


# Render selected page
page = PAGES[selection]
page.render()  # Each page has a render() function
