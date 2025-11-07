import streamlit as st


def render():
    st.title("📈 Analytics")
    st.write("This is the analytics page.")
    st.line_chart({"Sales": [100, 200, 300, 400]})
