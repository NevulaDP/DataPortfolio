import streamlit as st
import time

st.set_page_config(layout="wide")

st.markdown("""
<style>
    /* Full Page Center Container */
    .loading-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 70vh; /* Occupy most of the screen */
        width: 100%;
    }

    /* Glowing Spinner */
    .loader {
        width: 80px;
        height: 80px;
        border: 8px solid rgba(255, 255, 255, 0.1);
        border-left-color: #FF4B4B; /* Streamlit Red */
        border-radius: 50%;
        animation: spin 1.2s linear infinite;
        box-shadow: 0 0 20px rgba(255, 75, 75, 0.5);
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* Pulsing Text */
    .loading-text {
        margin-top: 30px;
        font-size: 24px;
        font-weight: 600;
        color: #FAFAFA;
        font-family: 'Source Sans Pro', sans-serif;
        animation: pulse-text 1.5s ease-in-out infinite;
    }

    @keyframes pulse-text {
        0% { opacity: 0.6; }
        50% { opacity: 1; }
        100% { opacity: 0.6; }
    }
</style>
""", unsafe_allow_html=True)

# Simulating the Loading Screen state
placeholder = st.empty()

steps = [
    "Drafting Scenario Narrative...",
    "Designing Data Recipe...",
    "Generating Synthetic Data...",
    "Verifying Data Quality..."
]

for step in steps:
    placeholder.markdown(f'''
        <div class="loading-container">
            <div class="loader"></div>
            <div class="loading-text">{step}</div>
        </div>
    ''', unsafe_allow_html=True)
    time.sleep(1.5)

placeholder.success("Done!")
