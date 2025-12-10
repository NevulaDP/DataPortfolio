import streamlit as st
import pandas as pd
import numpy as np
import io
import contextlib
import os
import traceback
import matplotlib.pyplot as plt
import seaborn as sns
import uuid
import ast
import sqlite3
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
if 'api_key' not in st.session_state:
    st.session_state.api_key = os.getenv("GEMINI_API_KEY", "")
if 'notebook_cells' not in st.session_state:
    st.session_state.notebook_cells = []
if 'notebook_scope' not in st.session_state:
    st.session_state.notebook_scope = {}
if 'sql_query' not in st.session_state:
    st.session_state.sql_query = "SELECT * FROM data LIMIT 10;"

# Initialize LLM Service (stateless)
llm_service = LLMService()

# --- Custom CSS for Layout ---
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
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

def init_notebook_state():
    # Initialize scope with common libraries and data
    st.session_state.notebook_scope = {
        'pd': pd,
        'np': np,
        'plt': plt,
        'sns': sns,
        'st': st,
        'df': st.session_state.get('project_data')
    }

    # Initial Cells
    if not st.session_state.notebook_cells:
        st.session_state.notebook_cells = [
            {
                "id": str(uuid.uuid4()),
                "type": "markdown",
                "content": "### Data Loading\nThe dataset has been pre-loaded into the variable `df`. Run the cell below to inspect it."
            },
            {
                "id": str(uuid.uuid4()),
                "type": "code",
                "content": "# The last expression in a cell is displayed automatically.\ndf.head()",
                "output": "",
                "result": None
            },
            {
                "id": str(uuid.uuid4()),
                "type": "markdown",
                "content": "### Analysis\nPerform your analysis below. To display a plot, return the figure object or use `st.pyplot()`."
            }
        ]

def execute_cell(cell_idx):
    cell = st.session_state.notebook_cells[cell_idx]
    code = cell['content']

    try:
        SafeExecutor.validate(code)
    except SecurityError as e:
        st.session_state.notebook_cells[cell_idx]['output'] = f"Security Error: {e}"
        st.session_state.notebook_cells[cell_idx]['result'] = None
        return

    output_buffer = io.StringIO()
    result_obj = None

    try:
        with contextlib.redirect_stdout(output_buffer):
            # Parse code to handle last expression
            try:
                tree = ast.parse(code)
            except SyntaxError:
                # If syntax error, just let exec fail
                exec(code, st.session_state.notebook_scope)
                tree = None

            if tree and tree.body:
                last_node = tree.body[-1]
                if isinstance(last_node, ast.Expr):
                    # Compile and exec everything before the last expression
                    if len(tree.body) > 1:
                        module = ast.Module(body=tree.body[:-1], type_ignores=[])
                        exec(compile(module, filename="<string>", mode="exec"), st.session_state.notebook_scope)

                    # Eval the last expression
                    expr = ast.Expression(body=last_node.value)
                    result_obj = eval(compile(expr, filename="<string>", mode="eval"), st.session_state.notebook_scope)
                else:
                    # No expression at end, just exec all
                    exec(code, st.session_state.notebook_scope)
            elif tree is None:
                pass # Already executed in except block
            else:
                # Empty code
                pass

        st.session_state.notebook_cells[cell_idx]['output'] = output_buffer.getvalue()
        st.session_state.notebook_cells[cell_idx]['result'] = result_obj

    except Exception as e:
        st.session_state.notebook_cells[cell_idx]['output'] = f"{type(e).__name__}: {e}"
        st.session_state.notebook_cells[cell_idx]['result'] = None

def add_cell(cell_type):
    new_cell = {
        "id": str(uuid.uuid4()),
        "type": cell_type,
        "content": "",
        "output": "",
        "result": None
    }
    st.session_state.notebook_cells.append(new_cell)

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

            if "error" in definition:
                st.error(definition["error"])
                return

            if 'recipe' in definition:
                df = project_generator.generate_dataset(definition['recipe'], rows=10000)
            else:
                st.error("Invalid recipe format received from AI.")
                return

            st.session_state.project = {
                "definition": definition,
                "data": df
            }

            # Put data in global session state and scope
            st.session_state['project_data'] = df
            init_notebook_state()

            # Initialize chat
            st.session_state.messages = [{
                "role": "assistant",
                "content": f"Hello! I'm your Senior Data Analyst mentor. I've prepared a project for you on **{definition['title']}**. Check out the scenario and let me know if you need help!"
            }]
        except Exception as e:
            st.error(f"Error generating project: {e}")
            traceback.print_exc()

# --- UI Components ---

@st.fragment
def render_notebook():
    st.caption("Python Notebook (Runs independently)")

    # Toolbar
    col_btn1, col_btn2, _ = st.columns([1, 1, 4])
    with col_btn1:
        if st.button("+ Code", use_container_width=True):
            add_cell("code")
            # No st.rerun() needed in fragment, automatic update
    with col_btn2:
        if st.button("+ Text", use_container_width=True):
            add_cell("markdown")

    st.divider()

    # Render Cells
    for idx, cell in enumerate(st.session_state.notebook_cells):
        cell_key = f"cell_{cell['id']}"

        if cell['type'] == 'markdown':
            tab_view, tab_edit = st.tabs(["Preview", "Edit"])
            with tab_view:
                if cell['content'].strip():
                    st.markdown(cell['content'])
                else:
                    st.info("Empty Markdown Cell")
            with tab_edit:
                new_content = st.text_area("Markdown Content", value=cell['content'], key=f"md_{cell_key}", height=150)
                if new_content != cell['content']:
                    st.session_state.notebook_cells[idx]['content'] = new_content

        elif cell['type'] == 'code':
            with st.container(border=True):
                # Editor
                response = code_editor(
                    cell['content'],
                    lang="python",
                    key=f"ce_{cell_key}",
                    height=150,
                    buttons=[{
                        "name": "Run",
                        "feather": "Play",
                        "primary": True,
                        "hasText": True,
                        "showWithIcon": True,
                        "commands": ["submit"],
                        "style": {"bottom": "0.44rem", "right": "0.4rem"}
                    }]
                )

                # Check for execution trigger
                if response['type'] == "submit" and response['text'] != "":
                    st.session_state.notebook_cells[idx]['content'] = response['text']
                    execute_cell(idx)
                    # No st.rerun(), output renders below immediately if state updated

                # Sync content
                if response['text'] != cell['content']:
                     st.session_state.notebook_cells[idx]['content'] = response['text']

                # Output Display
                if cell.get('output'):
                    st.caption("Output:")
                    st.text(cell['output'])

                # Result Object Display
                if cell.get('result') is not None:
                    st.write(cell['result'])

@st.fragment
def render_sql():
    st.caption("SQL Interface (Runs independently)")

    df = st.session_state.get('project_data')
    if df is None:
        st.error("No data available.")
        return

    # SQL Editor
    query = st.session_state.get('sql_query', 'SELECT * FROM data LIMIT 10;')

    response = code_editor(
        query,
        lang="sql",
        height=150,
        key="sql_editor",
        buttons=[{
            "name": "Run Query",
            "feather": "Play",
            "primary": True,
            "hasText": True,
            "showWithIcon": True,
            "commands": ["submit"],
            "style": {"bottom": "0.44rem", "right": "0.4rem"}
        }]
    )

    if response['text'] != "":
        st.session_state.sql_query = response['text']

    if response['type'] == "submit":
        # Execute Query
        try:
            conn = sqlite3.connect(':memory:')
            df.to_sql('data', conn, index=False, if_exists='replace')
            result = pd.read_sql_query(response['text'], conn)
            st.write(result)
            conn.close()
        except Exception as e:
            st.error(f"SQL Error: {e}")

def render_sidebar():
    with st.sidebar:
        st.title("Settings")
        val = st.text_input(
            "Gemini API Key",
            type="password",
            help="Enter your Google Gemini API Key. It is used only for this session and not stored.",
            key="api_key"
        )

        if st.session_state.api_key:
            st.success("API Key configured.")
        else:
            st.warning("No API Key set. Using Mock Mode.")

        st.divider()

def render_landing():
    st.title("Junior Data Analyst Portfolio Builder 🚀")
    st.markdown("""
    Welcome! This tool helps you build a data analytics portfolio by generating realistic projects.

    1. **Pick a Sector**: We'll generate a scenario and a messy, realistic dataset.
    2. **Analyze**: Use the built-in Jupyter Notebook to explore the data.
    3. **Get Mentorship**: A built-in AI mentor will guide you through the analysis.
    """)

    st.text_input("Enter a Sector (e.g., Retail, Healthcare, Finance)", key="sector_input")
    st.button("Start Project", on_click=generate_project, type="primary")

def render_workspace():
    project = st.session_state.project
    definition = project['definition']

    col_context, col_work = st.columns([1, 2], gap="large")

    # --- Chat & Context (Left Column) ---
    with col_context:
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

        chat_container = st.container(height=400)
        for msg in st.session_state.messages:
            chat_container.chat_message(msg["role"]).write(msg["content"])

        if prompt := st.chat_input("Ask for help..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            chat_container.chat_message("user").write(prompt)

            # Build Context from Notebook Cells
            notebook_context = []
            for cell in st.session_state.notebook_cells:
                notebook_context.append({
                    "cell_type": cell['type'],
                    "source": cell['content'],
                    "output": cell.get('output', '')
                })

            code_context = {"notebook": notebook_context}

            with st.spinner("Thinking..."):
                response = llm_service.generate_text(
                    prompt=prompt,
                    api_key=st.session_state.api_key,
                    project_context=definition,
                    code_context=code_context,
                    history=st.session_state.messages[:-1]
                )
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

    # --- Notebook & SQL (Right Column) ---
    with col_work:
        st.title("Workspace")

        tab_py, tab_sql = st.tabs(["Python", "SQL"])

        with tab_py:
            render_notebook()

        with tab_sql:
            render_sql()

# --- Main App Logic ---

render_sidebar()

if st.session_state.project is None:
    render_landing()
else:
    render_workspace()
