import streamlit as st


def render():
    st.title("⚙️ Settings")
    st.write("Here you can adjust your dashboard preferences.")
    theme = st.selectbox("Select Theme", ["Light", "Dark", "Auto"])
    st.success(f"Selected theme: {theme}")
