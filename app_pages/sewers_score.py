import streamlit as st
import pandas as pd

st.title("Sewers Score")

if "df" not in st.session_state or st.session_state.df is None:
    st.error("sewers_score dataframe not found in session state.")
    st.stop()

df = st.session_state.df.copy()

if df.empty:
    st.warning("sewers_score dataframe is empty.")
    st.stop()

st.subheader("Raw Sewers Score Data")
st.dataframe(df, use_container_width=True)