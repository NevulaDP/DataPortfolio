import streamlit as st
from streamlit_notebook import st_notebook

st.set_page_config(layout="wide")

if 'my_test_var' not in st.session_state:
    st.session_state.my_test_var = 42

nb = st_notebook()

if not nb.cells:
    nb.add_cell("x = 1", "code")

nb.render()

if nb.cells:
    st.write("Cell 0 attributes:")
    c = nb.cells[0]
    st.write(dir(c))
    st.write(f"Type: {c.cell_type}") # standard?
    st.write(f"Content: {c.content}") # or source?
