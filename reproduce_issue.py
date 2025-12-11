import streamlit as st
from streamlit_float import *

float_init()

st.title("Background Text")
for i in range(20):
    st.write(f"This is line {i} of background text to demonstrate transparency.")

# Test with Expander as in app.py
c = st.container()
with c:
    with st.expander("Mentor Chat", expanded=True):
        st.write("I am floating inside an expander")
        st.write("Is this transparent?")

# Using the exact CSS from app.py
c.float("bottom: 50px; right: 50px; width: 300px; background-color: var(--background-color); border: 2px solid blue; padding: 20px;")
