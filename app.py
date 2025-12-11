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
from streamlit_quill import st_quill
from streamlit_float import *
from services.generator import project_generator
from services.llm import LLMService
from services.security import SafeExecutor, SecurityError

# --- Page Config ---
st.set_page_config(
    page_title="Junior Data Analyst Portfolio Builder",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize float
float_init()

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
# Track editing state for cells: {cell_id: boolean}
if 'cell_edit_state' not in st.session_state:
    st.session_state.cell_edit_state = {}
# Track chat processing state
if 'processing_chat' not in st.session_state:
    st.session_state.processing_chat = False

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
    .stButton button {
        border-radius: 5px;
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
                "content": "### Data Loading<br>The dataset has been pre-loaded into the variable `df`. Run the cell below to inspect it."
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
                "content": "### Analysis<br>Perform your analysis below. To display a plot, return the figure object or use `st.pyplot()`."
            }
        ]
        # Set default edit state to False (Preview Mode) for initial text cells?
        # Or True (Edit Mode)? Let's go with True for new cells usually.
        for cell in st.session_state.notebook_cells:
            if cell['type'] == 'markdown':
                st.session_state.cell_edit_state[cell['id']] = True

def execute_cell(cell_idx):
    if cell_idx < 0 or cell_idx >= len(st.session_state.notebook_cells):
        return

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

def add_cell(cell_type, index=None):
    new_id = str(uuid.uuid4())
    new_cell = {
        "id": new_id,
        "type": cell_type,
        "content": "",
        "output": "",
        "result": None
    }

    # Default to edit mode for new markdown cells
    if cell_type == 'markdown':
        st.session_state.cell_edit_state[new_id] = True

    if index is not None and 0 <= index <= len(st.session_state.notebook_cells):
        st.session_state.notebook_cells.insert(index, new_cell)
    else:
        st.session_state.notebook_cells.append(new_cell)

def delete_cell(index):
    if 0 <= index < len(st.session_state.notebook_cells):
        cell_id = st.session_state.notebook_cells[index]['id']
        st.session_state.notebook_cells.pop(index)
        # Cleanup edit state
        if cell_id in st.session_state.cell_edit_state:
            del st.session_state.cell_edit_state[cell_id]
        st.rerun()

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

def toggle_edit_mode(cell_id):
    current_state = st.session_state.cell_edit_state.get(cell_id, True)
    st.session_state.cell_edit_state[cell_id] = not current_state

def send_chat_message():
    """Callback to send chat message and clear input."""
    if st.session_state.chat_input_text:
        st.session_state.messages.append({"role": "user", "content": st.session_state.chat_input_text})
        st.session_state.chat_input_text = ""
        st.session_state.processing_chat = True

# --- UI Components ---

def get_python_completions():
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

def get_sql_completions():
    completions = []

    # 1. Tables
    for table in ['df', 'data']:
        completions.append({
            "caption": table,
            "value": table,
            "meta": "Table",
            "score": 1000
        })

    # 2. Columns (from project_data)
    df = st.session_state.get('project_data')
    if df is not None:
         for col in df.columns:
            col_str = str(col)
            completions.append({
                "caption": col_str,
                "value": col_str,
                "meta": "Column",
                "score": 900
            })

    # 3. SQL Keywords (Basic list)
    keywords = [
        "SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "LIMIT",
        "JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "ON",
        "COUNT", "SUM", "AVG", "MIN", "MAX", "HAVING", "DISTINCT",
        "AS", "CASE", "WHEN", "THEN", "ELSE", "END", "LIKE", "IN"
    ]
    for kw in keywords:
        completions.append({
            "caption": kw,
            "value": kw,
            "meta": "Keyword",
            "score": 500
        })

    return completions

def render_add_cell_controls(index):
    """Renders a discreet add button that opens a popover to select cell type."""
    # Using a container and centering logic to make it look nice
    c1, c2, c3 = st.columns([5, 1, 5])
    with c2:
        with st.popover("➕", use_container_width=True):
            if st.button("Python", key=f"add_py_{index}", use_container_width=True):
                add_cell("code", index)
                st.rerun()
            if st.button("SQL", key=f"add_sql_{index}", use_container_width=True):
                add_cell("sql", index)
                st.rerun()
            if st.button("Text", key=f"add_txt_{index}", use_container_width=True):
                add_cell("markdown", index)
                st.rerun()

def render_floating_chat():
    project = st.session_state.project
    definition = project['definition']

    # Create a container for the floating chat
    chat_con = st.container()

    with chat_con:
        # Use an expander to allow collapsing/expanding
        # Defaulting to expanded so the user sees it immediately
        with st.expander("💬 Mentor Chat", expanded=True):
            # Message History
            chat_container = st.container(height=300)
            for msg in st.session_state.messages:
                chat_container.chat_message(msg["role"]).write(msg["content"])

            # Input Area
            # Using columns to place input and button side-by-side
            c_input, c_btn = st.columns([4, 1])
            with c_input:
                st.text_input("Message", key="chat_input_text", label_visibility="collapsed")
            with c_btn:
                st.button("Send", use_container_width=True, on_click=send_chat_message)

            # Processing LLM logic
            if st.session_state.processing_chat:
                # Build Context from Notebook Cells
                notebook_context = []
                for cell in st.session_state.notebook_cells:
                    notebook_context.append({
                        "cell_type": cell['type'],
                        "source": cell['content'],
                        "output": cell.get('output', '')
                    })

                code_context = {"notebook": notebook_context}

                # Call LLM
                with st.spinner("Thinking..."):
                     response = llm_service.generate_text(
                        prompt=st.session_state.messages[-1]["content"],
                        api_key=st.session_state.api_key,
                        project_context=definition,
                        code_context=code_context,
                        history=st.session_state.messages[:-2] # History excluding current msg
                    )
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.session_state.processing_chat = False
                st.rerun()

    # Float the container
    # Position shifted to 370px to clear sidebar when open
    # Added explicit background color variable to handle themes/transparency
    # Added border for visibility
    chat_con.float("bottom: 20px; left: 370px; width: 400px; z-index: 99999; background-color: var(--background-color); border: 1px solid var(--text-color-20); border-radius: 10px; padding: 10px;")


@st.fragment
def render_notebook():
    # Get current completions
    py_completions = get_python_completions()
    sql_completions = get_sql_completions()

    # Add Control at top
    render_add_cell_controls(0)

    # Render Cells
    for idx, cell in enumerate(st.session_state.notebook_cells):
        cell_key = f"cell_{cell['id']}"
        cell_id = cell['id']

        # Determine container styling based on type
        with st.container(border=True):
            # Top Bar: Label and Delete Button
            col_lbl, col_del = st.columns([1, 0.05])
            with col_del:
                if st.button("🗑️", key=f"del_{cell_key}", help="Delete Cell"):
                    delete_cell(idx)

            with col_lbl:
                if cell['type'] == 'markdown':
                    # Check Edit State
                    is_editing = st.session_state.cell_edit_state.get(cell_id, True)

                    # Label + Toggle Button
                    c_label, c_toggle = st.columns([0.9, 0.1])
                    with c_label:
                        st.caption("Text / Markdown")
                    with c_toggle:
                        if is_editing:
                            if st.button("👁️", key=f"toggle_prev_{cell_key}", help="Preview"):
                                toggle_edit_mode(cell_id)
                                st.rerun()
                        else:
                            if st.button("✏️", key=f"toggle_edit_{cell_key}", help="Edit"):
                                toggle_edit_mode(cell_id)
                                st.rerun()

                    if is_editing:
                        # Rich Text Editor
                        content = st_quill(
                            value=cell['content'],
                            placeholder="Write your analysis here...",
                            html=True,
                            key=f"quill_{cell_key}",
                            toolbar=[
                                ['bold', 'italic', 'underline', 'strike'],
                                ['blockquote', 'code-block'],
                                [{'size': ['small', False, 'large', 'huge']}],
                                [{'header': [1, 2, 3, 4, 5, 6, False]}],
                                [{'list': 'ordered'}, {'list': 'bullet'}],
                                [{'script': 'sub'}, {'script': 'super'}],
                                [{'indent': '-1'}, {'indent': '+1'}],
                                [{'direction': 'rtl'}],
                                [{'color': []}, {'background': []}],
                                [{'align': []}],
                                ['clean']
                            ]
                        )
                        # Sync content
                        if content != cell['content']:
                            st.session_state.notebook_cells[idx]['content'] = content
                    else:
                        # Preview Mode (Render HTML)
                        st.markdown(cell['content'], unsafe_allow_html=True)

                elif cell['type'] == 'code':
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
                            "scrollPastEnd": 0.5,
                        },
                        completions=py_completions,
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
                        st.divider()
                        st.caption("Output:")
                        st.text(cell['output'])

                    # Result Object Display
                    if cell.get('result') is not None:
                        st.write(cell['result'])

                elif cell['type'] == 'sql':
                    st.caption("SQL (DuckDB)")
                    # Editor
                    response = code_editor(
                        cell['content'],
                        lang="sql",
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
                            "scrollPastEnd": 0.5,
                        },
                        completions=sql_completions,
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
                        st.divider()
                        st.caption("Error:")
                        st.error(cell['output'])

                    # Result Object Display
                    if cell.get('result') is not None:
                        st.dataframe(cell['result'])

        # Render "Add" control after this cell (which corresponds to idx + 1)
        render_add_cell_controls(idx + 1)

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

    # --- Context (Left Column) ---
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

    # --- Notebook (Right Column) ---
    with col_work:
        st.title("Workspace")
        if df is not None:
            # Data Preview
            st.subheader("Data Preview")
            st.dataframe(df.head(), use_container_width=True)

            # Download
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Data", csv, "project_data.csv", "text/csv")

        st.divider()

        render_notebook()

    # --- Floating Chat ---
    render_floating_chat()

# --- Main App Logic ---

render_sidebar()

if st.session_state.project is None:
    render_landing()
else:
    render_workspace()
