import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import io
import contextlib
import os
import traceback
import matplotlib.pyplot as plt
import seaborn as sns
import ast
from code_editor import code_editor
from services.generator import project_generator
from services.llm import LLMService
from services.security import SafeExecutor, SecurityError

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
if 'python_code' not in st.session_state:
    st.session_state.python_code = "# Calculate summary statistics\nprint(df.describe())\n\n# Plotting example\n# plt.figure(figsize=(10, 6))\n# sns.histplot(df['amount'])\n# plt.show()"
if 'sql_code' not in st.session_state:
    st.session_state.sql_code = "SELECT * FROM dataset LIMIT 10"
if 'api_key' not in st.session_state:
    st.session_state.api_key = os.getenv("GEMINI_API_KEY", "")

# Initialize LLM Service (stateless)
llm_service = LLMService()

# --- Custom CSS for Layout ---
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .console-output {
        font-family: 'Courier New', Courier, monospace;
        background-color: #0e1117;
        color: #fafafa;
        padding: 10px;
        border-radius: 5px;
        white-space: pre-wrap;
        max-height: 300px;
        overflow-y: auto;
    }
    .console-error {
        color: #ff4b4b;
    }
    /* Fix for dropdown cropping: set overflow visible on Ace containers */
    .ace_editor, .ace_editor * {
        overflow: visible !important;
    }
    .ace_autocomplete {
        z-index: 99999 !important;
    }
    /* Better styling for scenario box */
    .scenario-box {
        background-color: #1e1e1e;
        color: #e0e0e0;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
        margin-bottom: 20px;
    }
    .scenario-title {
        font-size: 1.5rem;
        font-weight: bold;
        color: #4CAF50;
        margin-bottom: 10px;
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
            definition = project_generator.generate_project_definition(
                st.session_state.sector_input,
                st.session_state.api_key
            )

            # Check for error in definition (e.g. 404 from LLM)
            if "error" in definition:
                st.error(definition["error"])
                return

            # Use the new 'recipe' key for generation
            # Pass explicit rows=10000 per requirement
            if 'recipe' in definition:
                df = project_generator.generate_dataset(definition['recipe'], rows=10000)
            else:
                st.error("Invalid recipe format received from AI.")
                return

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
            traceback.print_exc()

def run_sql(query, df):
    try:
        conn = sqlite3.connect(':memory:')
        df.to_sql('dataset', conn, index=False, if_exists='replace')
        result = pd.read_sql_query(query, conn)
        return result, None
    except Exception as e:
        return None, str(e)

def run_python(code, df):
    # Security Check
    try:
        SafeExecutor.validate(code)
    except SecurityError as e:
        return None, str(e), [], None

    # Capture stdout
    output_buffer = io.StringIO()

    # Context for execution: Provide pandas, numpy, seaborn, matplotlib, etc.
    local_scope = {
        "df": df,
        "pd": pd,
        "np": np,
        "plt": plt,
        "sns": sns,
        "st": st
    }

    figures = []
    error_message = None
    last_value = None

    try:
        with contextlib.redirect_stdout(output_buffer):
            # Parse code to check for last expression
            tree = ast.parse(code)
            if tree.body and isinstance(tree.body[-1], ast.Expr):
                # Separate last expression
                last_expr = tree.body.pop()
                # Compile and run the preamble
                if tree.body:
                    exec_code = compile(tree, filename="<string>", mode="exec")
                    exec(exec_code, {}, local_scope)

                # Compile and eval the last expression
                eval_code = compile(ast.Expression(last_expr.value), filename="<string>", mode="eval")
                last_value = eval(eval_code, {}, local_scope)
            else:
                exec(code, {}, local_scope)

        # Check for open figures
        if plt.get_fignums():
            fignums = plt.get_fignums()
            for i in fignums:
                figures.append(plt.figure(i))

    except Exception:
        error_message = traceback.format_exc()

    return output_buffer.getvalue(), error_message, figures, last_value

# --- UI Components ---

def render_sidebar():
    with st.sidebar:
        st.title("Settings")

        # API Key Input
        st.text_input(
            "Gemini API Key",
            type="password",
            help="Enter your Google Gemini API Key. It is used only for this session and not stored.",
            key="api_key"
        )

        if st.session_state.api_key:
            st.success("API Key configured for this session.")
        else:
            st.warning("No API Key set. Using Mock Mode.")

        st.divider()

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

    # Split layout: Left (Context) vs Right (Work)
    col_context, col_work = st.columns([1, 2], gap="large")

    with col_context:
        # Improved Scenario UI
        st.markdown(f"""
        <div class="scenario-box">
            <div class="scenario-title">{definition['title']}</div>
            <p>{definition['description']}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Tasks", expanded=True):
            for i, task in enumerate(definition['tasks']):
                st.write(f"{i+1}. {task}")

        with st.expander("Data Schema"):
            schema = definition.get('display_schema', definition.get('schema', []))
            for col in schema:
                st.write(f"**{col['name']}** ({col['type']})")

        st.divider()
        st.header("💬 Mentor Chat")

        # Chat History
        chat_container = st.container(height=400)
        for msg in st.session_state.messages:
            chat_container.chat_message(msg["role"]).write(msg["content"])

        # Chat Input
        if prompt := st.chat_input("Ask for help..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            chat_container.chat_message("user").write(prompt)

            # Prepare context including code
            code_context = {
                "python": st.session_state.python_code,
                "sql": st.session_state.sql_code
            }

            # Generate response
            # Use gemma-3-27b-it via LLMService
            response = llm_service.generate_text(
                prompt=prompt,
                api_key=st.session_state.api_key,
                project_context=definition,
                code_context=code_context,
                history=st.session_state.messages[:-1]
            )

            st.session_state.messages.append({"role": "assistant", "content": response})
            chat_container.chat_message("assistant").write(response)

    with col_work:
        st.title(f"Workspace")

        # Data Preview
        with st.expander("Data Preview (First 5 rows)", expanded=False):
            st.dataframe(df.head())

        # Editors
        tab_python, tab_sql = st.tabs(["🐍 Python Analysis", "💾 SQL Query"])

        with tab_python:
            st.markdown("Use `df` to access the dataset. Available: `pd`, `np`, `plt`, `sns`.")
            st.info("💡 Tip: Use `plt.show()` or `plt.plot()` to render figures.")

            # Python Editor with advanced options
            response_dict_py = code_editor(
                st.session_state.python_code,
                key="python_editor",
                lang="python",
                height=600,
                theme="dawn",
                options={
                    "showLineNumbers": True,
                    "wrap": True,
                    "autoScrollEditorIntoView": True,
                    "enableBasicAutocompletion": True,
                    "enableLiveAutocompletion": True,
                    "enableSnippets": True,
                    "fontSize": 14,
                    "fontFamily": "monospace"
                },
                buttons=[{
                    "name": "Run",
                    "feather": "Play",
                    "primary": True,
                    "hasText": True,
                    "alwaysOn": True,
                    "commands": ["submit"],
                    "style": {"bottom": "0.46rem", "right": "0.4rem"}
                },
                {
                    "name": "Stop",
                    "feather": "Square",
                    "primary": False,
                    "hasText": True,
                    "alwaysOn": True,
                    "commands": ["stop"],
                    "style": {"bottom": "0.46rem", "right": "6rem"}
                }]
            )

            # Debugging

            # Always sync state with editor content
            if response_dict_py['text'] != st.session_state.python_code and response_dict_py['text']:
                 st.session_state.python_code = response_dict_py['text']

            if response_dict_py['type'] == "submit" and len(response_dict_py['text']) != 0:
                output, error, figs, last_value = run_python(response_dict_py['text'], df)

                # Console Output
                st.markdown("**Console Output:**")
                if output:
                    st.markdown(f'<div class="console-output">{output}</div>', unsafe_allow_html=True)
                elif not error and last_value is None:
                     st.markdown(f'<div class="console-output" style="color: #888;">No textual output</div>', unsafe_allow_html=True)

                # Display Last Value (REPL style)
                if last_value is not None:
                    st.markdown("**Result:**")
                    if isinstance(last_value, (pd.DataFrame, pd.Series)):
                        st.dataframe(last_value)
                    else:
                        st.write(last_value)

                # Error Output
                if error:
                    st.markdown("**Error:**")
                    st.markdown(f'<div class="console-output console-error">{error}</div>', unsafe_allow_html=True)

                # Plots
                if figs:
                    st.markdown("**Plots:**")
                    for fig in figs:
                        st.pyplot(fig)
                        plt.close(fig) # Cleanup

            elif response_dict_py['type'] == "stop":
                # Clear output by doing nothing (since output rendering is inside the submit block)
                # But to be explicit and perhaps handle persistence if I add it later:
                pass

        with tab_sql:
            st.markdown("Table name is `dataset`.")

            # SQL Editor
            response_dict_sql = code_editor(
                st.session_state.sql_code,
                key="sql_editor",
                lang="sql",
                height=600,
                theme="dawn",
                options={
                    "showLineNumbers": True,
                    "wrap": True,
                    "fontSize": 14,
                },
                 buttons=[{
                    "name": "Run",
                    "feather": "Play",
                    "primary": True,
                    "hasText": True,
                    "alwaysOn": True,
                    "commands": ["submit"],
                    "style": {"bottom": "0.46rem", "right": "0.4rem"}
                },
                {
                    "name": "Stop",
                    "feather": "Square",
                    "primary": False,
                    "hasText": True,
                    "alwaysOn": True,
                    "commands": ["stop"],
                    "style": {"bottom": "0.46rem", "right": "6rem"}
                }]
            )

            # Always sync state with editor content
            if response_dict_sql['text'] != st.session_state.sql_code and response_dict_sql['text']:
                 st.session_state.sql_code = response_dict_sql['text']

            if response_dict_sql['type'] == "submit" and len(response_dict_sql['text']) != 0:
                res, error = run_sql(response_dict_sql['text'], df)

                st.markdown("**Results:**")
                if res is not None:
                    st.dataframe(res)
                if error:
                    st.markdown(f'<div class="console-output console-error">{error}</div>', unsafe_allow_html=True)

            elif response_dict_sql['type'] == "stop":
                pass

            elif response_dict_sql['text'] != st.session_state.sql_code and response_dict_sql['text']:
                 st.session_state.sql_code = response_dict_sql['text']

# --- Main App Logic ---

render_sidebar()

if st.session_state.project is None:
    render_landing()
else:
    render_workspace()
