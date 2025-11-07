import streamlit as st
from pages import home, analytics, settings

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
}

selection = st.sidebar.radio("Go to", list(PAGES.keys()))

# Render selected page
page = PAGES[selection]
page.render()  # Each page has a render() function
