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
import duckdb
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
    cell_type = cell['type']

    if cell_type == 'code':
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

    elif cell_type == 'sql':
        try:
            # Connect to DuckDB
            con = duckdb.connect()

            # Register the dataframe if it exists
            df = st.session_state.get('project_data')
            if df is not None:
                # Register as both 'df' and 'data' for convenience
                con.register('df', df)
                con.register('data', df)

                try:
                    # Execute Query and return as DataFrame
                    result_df = con.execute(code).df()
                    st.session_state.notebook_cells[cell_idx]['result'] = result_df
                    st.session_state.notebook_cells[cell_idx]['output'] = ""
                except Exception as e:
                    st.session_state.notebook_cells[cell_idx]['output'] = f"SQL Error: {e}"
                    st.session_state.notebook_cells[cell_idx]['result'] = None
            else:
                 st.session_state.notebook_cells[cell_idx]['output'] = "No dataset available."
        except Exception as e:
             st.session_state.notebook_cells[cell_idx]['output'] = f"Error: {e}"

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

def get_completions():
    completions = []

    # 1. Scope Variables
    scope = st.session_state.get('notebook_scope', {})
    for var_name, var_val in scope.items():
        if var_name.startswith('_'): continue
        meta_type = type(var_val).__name__

        # Add variable itself
        completions.append({
            "caption": var_name,
            "value": var_name,
            "meta": meta_type,
            "score": 1000
        })

        # If it's a dataframe, add columns
        if isinstance(var_val, pd.DataFrame):
            for col in var_val.columns:
                col_str = str(col)
                # Add as string literal (useful for df['...'])
                completions.append({
                    "caption": col_str,
                    "value": f"'{col_str}'",
                    "meta": "column",
                    "score": 900
                })
                # Add as attribute if valid identifier
                if col_str.isidentifier():
                     completions.append({
                        "caption": col_str,
                        "value": col_str,
                        "meta": "column",
                        "score": 800
                    })

    # 3. Common Methods (Static list for standard libraries)
    # This helps users with common pandas/numpy/plotting operations
    common_methods = [
        # Pandas
        "head", "tail", "describe", "info", "columns", "index", "dtypes",
        "shape", "groupby", "merge", "concat", "pivot_table", "plot",
        "value_counts", "sort_values", "fillna", "dropna", "apply", "map",
        "read_csv", "to_csv",
        # Numpy
        "array", "arange", "linspace", "mean", "sum", "std", "min", "max",
        # Matplotlib/Seaborn
        "figure", "title", "xlabel", "ylabel", "show", "scatterplot",
        "lineplot", "barplot", "histplot", "boxplot", "heatmap"
    ]

    for method in common_methods:
        completions.append({
            "caption": method,
            "value": method,
            "meta": "method",
            "score": 500
        })

    return completions

@st.fragment
def render_notebook():
    # Get current completions
    completions = get_completions()

    # Toolbar
    col_btn1, col_btn2, col_btn3, _ = st.columns([1, 1, 1, 3])
    with col_btn1:
        if st.button("+ Code", use_container_width=True):
            add_cell("code")
    with col_btn2:
        if st.button("+ SQL", use_container_width=True):
            add_cell("sql")
    with col_btn3:
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
                st.caption("Python")
                # Editor
                response = code_editor(
                    cell['content'],
                    lang="python",
                    key=f"ce_{cell_key}",
                    height=250,
                    options={
                        "displayIndentGuides": True,
                        "highlightActiveLine": True,
                        "wrap": True,
                        "enableLiveAutocompletion": True,
                        "enableBasicAutocompletion": True,
                        "enableSnippets": True,
                        "minLines": 10,
                        "maxLines": 20,
                        "scrollPastEnd": 0.5, # Helps with bottom clipping by allowing scroll
                    },
                    completions=completions,
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

        elif cell['type'] == 'sql':
            with st.container(border=True):
                st.caption("SQL (DuckDB)")
                # Editor
                response = code_editor(
                    cell['content'],
                    lang="sql",
                    key=f"ce_{cell_key}",
                    height=200,
                    options={
                        "wrap": True,
                        "scrollPastEnd": 0.5,
                    },
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

                # Sync content
                if response['text'] != cell['content']:
                     st.session_state.notebook_cells[idx]['content'] = response['text']

                # Output Display
                if cell.get('output'):
                    st.caption("Error:")
                    st.error(cell['output'])

                # Result Object Display
                if cell.get('result') is not None:
                    st.dataframe(cell['result'])

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
    df = st.session_state.get('project_data')

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

    # --- Notebook (Right Column) ---
    with col_work:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.title("Workspace")
        with c2:
            if df is not None:
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download Data", csv, "project_data.csv", "text/csv", use_container_width=True)

        render_notebook()

# --- Main App Logic ---

render_sidebar()

if st.session_state.project is None:
    render_landing()
else:
    render_workspace()
