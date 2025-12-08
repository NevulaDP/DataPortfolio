import streamlit as st
import pandas as pd
import sqlite3
import io
import contextlib
from services.generator import project_generator
from services.llm import llm_service

# --- Page Config ---
st.set_page_config(
    page_title="Junior Data Analyst Portfolio Builder",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Management ---
if 'project' not in st.session_state:
    st.session_state.project = None
if 'messages' not in st.session_state:
    st.session_state.messages = []

# --- Custom CSS for Layout ---
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Functions ---

def generate_project():
    if not st.session_state.sector_input:
        st.error("Please enter a sector.")
        return

    with st.spinner(f"Generating synthetic data and scenario for '{st.session_state.sector_input}'..."):
        try:
            definition = project_generator.generate_project_definition(st.session_state.sector_input)
            df = project_generator.generate_dataset(definition.get('schema', []), rows=500)

            st.session_state.project = {
                "definition": definition,
                "data": df
            }
            # Initialize chat with a welcome message
            st.session_state.messages = [{
                "role": "assistant",
                "content": f"Hello! I'm your Senior Data Analyst mentor. I've prepared a project for you on **{definition['title']}**. Check out the scenario and let me know if you need help!"
            }]
        except Exception as e:
            st.error(f"Error generating project: {e}")

def run_sql(query, df):
    try:
        conn = sqlite3.connect(':memory:')
        df.to_sql('dataset', conn, index=False, if_exists='replace')
        result = pd.read_sql_query(query, conn)
        return result, None
    except Exception as e:
        return None, str(e)

def run_python(code, df):
    # Capture stdout
    output_buffer = io.StringIO()

    # Context for execution
    local_scope = {"df": df, "pd": pd}

    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(code, {}, local_scope)
        return output_buffer.getvalue(), None
    except Exception as e:
        return output_buffer.getvalue(), str(e)

# --- UI Components ---

def render_landing():
    st.title("Junior Data Analyst Portfolio Builder 🚀")
    st.markdown("""
    Welcome! This tool helps you build a data analytics portfolio by generating realistic projects.

    1. **Pick a Sector**: We'll generate a scenario and a messy, realistic dataset.
    2. **Analyze**: Use the built-in SQL and Python editors to explore the data.
    3. **Get Mentorship**: A built-in AI mentor will guide you through the analysis.
    """)

    st.text_input("Enter a Sector (e.g., Retail, Healthcare, Finance)", key="sector_input")
    st.button("Start Project", on_click=generate_project, type="primary")

def render_workspace():
    project = st.session_state.project
    definition = project['definition']
    df = project['data']

    # --- Sidebar: Scenario & Chat ---
    with st.sidebar:
        st.header("📋 Project Scenario")
        st.subheader(definition['title'])
        st.info(definition['description'])

        with st.expander("Tasks", expanded=True):
            for i, task in enumerate(definition['tasks']):
                st.write(f"{i+1}. {task}")

        with st.expander("Data Schema"):
            for col in definition['schema']:
                st.write(f"**{col['name']}** ({col['type']})")

        st.divider()
        st.header("💬 Mentor Chat")

        # Chat History
        chat_container = st.container(height=300)
        for msg in st.session_state.messages:
            chat_container.chat_message(msg["role"]).write(msg["content"])

        # Chat Input
        if prompt := st.chat_input("Ask for help..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            chat_container.chat_message("user").write(prompt)

            # Generate response
            context = f"Project: {definition['title']}. Scenario: {definition['description']}"
            full_prompt = f"You are a Senior Data Analyst mentor. The user is a Junior Analyst working on a project.\nContext: {context}\n\nUser: {prompt}\nMentor:"
            response = llm_service.generate_text(full_prompt)

            st.session_state.messages.append({"role": "assistant", "content": response})
            chat_container.chat_message("assistant").write(response)

    # --- Main Area: Workspace ---
    st.title(f"Workspace: {definition['title']}")

    # Data Preview
    with st.expander("Data Preview (First 5 rows)", expanded=False):
        st.dataframe(df.head())

    # Editors
    tab_python, tab_sql = st.tabs(["🐍 Python Analysis", "💾 SQL Query"])

    with tab_python:
        st.markdown("Use `df` to access the dataset.")
        st.warning("⚠️ Code is executed on the server. Do not run malicious code.")
        code_py = st.text_area("Python Code", value="# Calculate summary statistics\nprint(df.describe())", height=200, key="py_editor")
        if st.button("Run Python", key="run_py"):
            output, error = run_python(code_py, df)
            if output:
                st.text("Output:")
                st.code(output)
            if error:
                st.error(f"Error: {error}")

    with tab_sql:
        st.markdown("Table name is `dataset`.")
        code_sql = st.text_area("SQL Query", value="SELECT * FROM dataset LIMIT 10", height=200, key="sql_editor")
        if st.button("Run SQL", key="run_sql"):
            res, error = run_sql(code_sql, df)
            if res is not None:
                st.dataframe(res)
            if error:
                st.error(f"Error: {error}")

# --- Main App Logic ---

if st.session_state.project is None:
    render_landing()
else:
    render_workspace()
