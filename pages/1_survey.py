import streamlit as st

st.set_page_config(page_title="Survey", page_icon="📋")

st.title("📋 Profile Setup")
st.info("The survey now opens as a popup on the home page.")
st.page_link("app.py", label="Go to Home to set up your profile →", icon="🏠")
