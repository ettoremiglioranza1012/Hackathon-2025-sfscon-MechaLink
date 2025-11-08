import streamlit as st
import pandas as pd


def render():
    # Titolo
    st.title("Robot Task Dashboard")

    # Tabs principali
    tabs = st.tabs(["🧹 Cleaning", "📦 Delivery", "🏗️ Lifting"])

