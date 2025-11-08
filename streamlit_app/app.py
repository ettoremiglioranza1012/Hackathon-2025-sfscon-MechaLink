import streamlit as st
from pages import home, analytics, settings, task
from datetime import datetime
from utils.helpers import (
    retrieve_and_plot_shop_analysis,
    retrieve_and_plot_shop_cleaning,
    retrieve_and_plot_shop_cleaning_detail,
    retrieve_and_plot_shop_industrial,
    retrieve_and_plot_shop_delivery,
    retrieve_and_plot_shop_cruise,
    retrieve_and_plot_shop_leading,
    retrieve_and_plot_shop_robots_general,
    retrieve_and_plot_shop_robots_operations,
)

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

retrieve_and_plot_shop_cleaning_detail(
    start_time=datetime(2025, 10, 1), end_time=(datetime(2025, 10, 31))
)

retrieve_and_plot_shop_cleaning(
    start_time=datetime(2025, 10, 1), end_time=(datetime(2025, 10, 31))
)

retrieve_and_plot_shop_industrial(
    start_time=datetime(2025, 10, 1), end_time=(datetime(2025, 10, 31))
)

retrieve_and_plot_shop_delivery(
    start_time=datetime(2025, 10, 1), end_time=(datetime(2025, 10, 31))
)

retrieve_and_plot_shop_cruise(
    start_time=datetime(2025, 10, 1), end_time=(datetime(2025, 10, 31))
)

retrieve_and_plot_shop_leading(
    start_time=datetime(2025, 10, 1), end_time=(datetime(2025, 10, 31))
)

retrieve_and_plot_shop_robots_general(
    start_time=datetime(2025, 10, 1), end_time=(datetime(2025, 10, 31))
)

retrieve_and_plot_shop_robots_operations(
    start_time=datetime(2025, 10, 1), end_time=(datetime(2025, 10, 31))
)


# Render selected page
page = PAGES[selection]
page.render()  # Each page has a render() function
