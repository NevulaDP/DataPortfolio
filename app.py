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
from services.report_generator import generate_html_report
from services.verifier import VerifierService
from services.session_manager import serialize_session, deserialize_session

# --- Page Config ---
st.set_page_config(
    page_title="Junior Data Analyst Portfolio Builder",
    page_icon="logo.png",
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
# Track chat window state (Open/Closed)
if 'chat_open' not in st.session_state:
    st.session_state.chat_open = False
# Track history of generated project titles/companies to prevent repetition
if 'generated_history' not in st.session_state:
    st.session_state.generated_history = []
if 'verification_result' not in st.session_state:
    st.session_state.verification_result = None
if 'generation_phase' not in st.session_state:
    st.session_state.generation_phase = 'idle' # idle, generating, complete

# Initialize LLM Service (stateless)
llm_service = LLMService()
verifier_service = VerifierService()

# --- Custom CSS for Layout ---
st.markdown("""
<style>
    /* --- CSS Variables (Theme System) --- */
    :root {
        /* Default Dark Theme (Deep Navy) */
        --bg-app: #06090e; /* Very dark navy/black */
        --bg-sidebar: #0b0f19; /* Slightly lighter navy */
        --bg-card: #0d1117; /* Card background */
        --bg-card-header: #161b22; /* Card header background */

        --text-primary: #ffffff;
        --text-secondary: #8b949e;
        --text-accent: #58a6ff;

        --border-color: #30363d;

        --accent-orange: #f29b3b;
        --accent-pink: #ff8080;
        --accent-green: #238636;

        --radius-large: 16px;
        --radius-small: 6px;
    }

    /* Light Mode Overrides */
    body.st-theme-light {
        --bg-app: #ffffff;
        --bg-sidebar: #f6f8fa;
        --bg-card: #ffffff;
        --bg-card-header: #f6f8fa;

        --text-primary: #24292f;
        --text-secondary: #57606a;
        --text-accent: #0969da;

        --border-color: #d0d7de;

        --accent-orange: #cf6615;
        --accent-pink: #cf222e;
        --accent-green: #1a7f37;
    }

    /* Apply Backgrounds */
    .stApp {
        background-color: var(--bg-app);
    }

    section[data-testid="stSidebar"] {
        background-color: var(--bg-sidebar);
        border-right: 1px solid var(--border-color);
    }

    /* --- Components Styling --- */

    /* Buttons (Generic) */
    .stButton button {
        border-radius: var(--radius-large);
        font-weight: 600;
    }

    /* Card Container */
    .card-container {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-large);
        margin-bottom: 1.5rem;
        overflow: hidden;
    }

    .card-header {
        background-color: var(--bg-card-header);
        border-bottom: 1px solid var(--border-color);
        padding: 0.5rem 1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .card-header-title {
        color: var(--text-secondary);
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .card-body {
        padding: 1rem;
    }

    /* MISSION HUB (Sidebar) Styling */
    .mission-hub-header {
        font-family: 'Source Sans Pro', sans-serif;
        font-weight: 800;
        letter-spacing: 1px;
        text-transform: uppercase;
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
        color: var(--text-primary);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .mission-scope {
        font-size: 0.7rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 2rem;
    }

    .mission-sub {
        font-size: 0.7rem;
        color: var(--accent-orange);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Top Navigation Bar */
    .top-nav-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--border-color);
    }

    .nav-pill-container {
        display: flex;
        background-color: var(--bg-card-header);
        border-radius: 20px;
        padding: 4px;
        border: 1px solid var(--border-color);
    }

    .nav-pill {
        padding: 6px 16px;
        border-radius: 16px;
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--text-secondary);
        cursor: pointer;
        transition: all 0.2s;
        text-decoration: none;
    }

    .nav-pill.active {
        background-color: var(--border-color); /* Highlight color */
        color: var(--text-primary);
    }

    .workspace-status {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        background-color: var(--accent-green);
        border-radius: 50%;
        box-shadow: 0 0 5px var(--accent-green);
    }

    /* Enhanced Loader Styles (Preserved) */
    .loading-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 70vh;
        width: 100%;
    }
    .loading-text {
        margin-top: 30px;
        font-size: 24px;
        font-weight: 600;
        color: var(--text-primary);
        font-family: 'Source Sans Pro', sans-serif;
        animation: pulse-text 1.5s ease-in-out infinite;
    }
    @keyframes pulse-text {
        0% { opacity: 0.6; }
        50% { opacity: 1; }
        100% { opacity: 0.6; }
    }

    /* Code Editor Overrides */
    iframe[title="code_editor.code_editor"] {
        border-radius: 0 0 var(--radius-large) var(--radius-large) !important;
    }

    /* --- Negative Margin Card Header Strategy --- */
    .card-header-wrapper {
        margin: -1rem -1rem 1rem -1rem;
        padding: 0.75rem 1rem;
        background-color: var(--bg-card-header);
        border-bottom: 1px solid var(--border-color);
        width: calc(100% + 2rem);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* --- Pill Navigation Styling (st.radio) --- */
    div[data-testid="stRadio"] > div[role="radiogroup"] {
        display: flex;
        flex-direction: row;
        gap: 0px;
        background-color: var(--bg-card-header);
        padding: 4px;
        border-radius: 24px;
        border: 1px solid var(--border-color);
        width: fit-content;
    }

    div[data-testid="stRadio"] label {
        background-color: transparent;
        border: none;
        padding: 6px 16px;
        border-radius: 20px;
        margin: 0;
        transition: all 0.2s;
    }

    div[data-testid="stRadio"] label p {
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        color: var(--text-secondary);
    }

    /* Active State Mocking */
    div[data-testid="stRadio"] label[data-checked="true"] {
        background-color: var(--bg-app);
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        color: var(--text-primary) !important;
    }

    div[data-testid="stRadio"] label[data-checked="true"] p {
        color: var(--text-primary) !important;
    }

    /* Hide the default radio circles */
    div[data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }

</style>
""", unsafe_allow_html=True)

# Inject JS for Theme Detection (Preserved)
import streamlit.components.v1 as components
components.html(r"""
<script>
    function checkTheme() {
        try {
            const parentDoc = window.parent.document;
            const body = parentDoc.body;
            const computedStyle = window.parent.getComputedStyle(body);
            const bgColor = computedStyle.backgroundColor;
            const rgb = bgColor.match(/\d+/g);
            if (rgb) {
                const r = parseInt(rgb[0]);
                const g = parseInt(rgb[1]);
                const b = parseInt(rgb[2]);
                const brightness = (r * 299 + g * 587 + b * 114) / 1000;
                if (brightness < 128) {
                    body.classList.add('st-theme-dark');
                    body.classList.remove('st-theme-light');
                } else {
                    body.classList.remove('st-theme-dark');
                    body.classList.add('st-theme-light');
                }
            }
        } catch (e) {
            console.error("Theme detection error:", e);
        }
    }
    setInterval(checkTheme, 500);
    checkTheme();
</script>
""", height=0, width=0)

# --- Functions ---

def load_session_callback():
    uploaded_file = st.session_state.get('session_uploader')
    if uploaded_file is not None:
        try:
            content = uploaded_file.getvalue().decode("utf-8")
            new_state = deserialize_session(content)
            if new_state:
                st.session_state.project = new_state['project']
                st.session_state.notebook_cells = new_state['notebook_cells']
                st.session_state.messages = new_state['messages']
                st.session_state.generated_history = new_state['generated_history']
                st.session_state.project_data = new_state['project_data']
                init_notebook_state()
                st.toast("Session loaded successfully!", icon="✅")
            else:
                st.error("Failed to parse session file.")
        except Exception as e:
            st.error(f"Error loading session: {e}")

def init_notebook_state():
    st.session_state.notebook_scope = {
        'df': st.session_state.get('project_data')
    }
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
        for cell in st.session_state.notebook_cells:
            if cell['type'] == 'markdown':
                st.session_state.cell_edit_state[cell['id']] = True

def get_execution_scope():
    scope = st.session_state.notebook_scope.copy()
    scope.update({'pd': pd, 'np': np, 'plt': plt, 'sns': sns, 'st': st})
    return scope

def update_persistent_scope(exec_scope):
    EXCLUDED_KEYS = {'pd', 'np', 'plt', 'sns', 'st'}
    for key, val in exec_scope.items():
        if key.startswith('_'): continue
        if key in EXCLUDED_KEYS: continue
        st.session_state.notebook_scope[key] = val
    persistent_keys = list(st.session_state.notebook_scope.keys())
    for key in persistent_keys:
        if key not in exec_scope:
            del st.session_state.notebook_scope[key]

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
        exec_scope = get_execution_scope()
        try:
            with contextlib.redirect_stdout(output_buffer):
                try:
                    tree = ast.parse(code)
                except SyntaxError:
                    exec(code, exec_scope)
                    tree = None
                if tree and tree.body:
                    last_node = tree.body[-1]
                    if isinstance(last_node, ast.Expr):
                        if len(tree.body) > 1:
                            module = ast.Module(body=tree.body[:-1], type_ignores=[])
                            exec(compile(module, filename="<string>", mode="exec"), exec_scope)
                        expr = ast.Expression(body=last_node.value)
                        result_obj = eval(compile(expr, filename="<string>", mode="eval"), exec_scope)
                    else:
                        exec(code, exec_scope)
            update_persistent_scope(exec_scope)
            st.session_state.notebook_cells[cell_idx]['output'] = output_buffer.getvalue()
            st.session_state.notebook_cells[cell_idx]['result'] = result_obj
        except Exception as e:
            st.session_state.notebook_cells[cell_idx]['output'] = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            st.session_state.notebook_cells[cell_idx]['result'] = None
    elif cell_type == 'sql':
        try:
            con = duckdb.connect()
            exec_scope = get_execution_scope()
            for var_name, var_val in exec_scope.items():
                if isinstance(var_val, pd.DataFrame):
                    try:
                        con.register(var_name, var_val)
                        if var_name == 'df':
                            con.register('data', var_val)
                    except Exception: pass
            try:
                result_df = con.execute(code).df()
                st.session_state.notebook_scope['last_sql_result'] = result_df
                st.session_state.notebook_cells[cell_idx]['result'] = result_df
                st.session_state.notebook_cells[cell_idx]['output'] = ""
            except Exception as e:
                st.session_state.notebook_cells[cell_idx]['output'] = f"SQL Error: {e}"
                st.session_state.notebook_cells[cell_idx]['result'] = None
        except Exception as e:
             st.session_state.notebook_cells[cell_idx]['output'] = f"Error: {e}"

def add_cell(cell_type, index=None):
    new_id = str(uuid.uuid4())
    new_cell = {"id": new_id, "type": cell_type, "content": "", "output": "", "result": None}
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
        if cell_id in st.session_state.cell_edit_state:
            del st.session_state.cell_edit_state[cell_id]
        st.rerun()

def render_loading_screen(placeholder):
    # Pass history to prevent repetition
    history_context = st.session_state.generated_history[-5:] # Keep last 5 context items

    placeholder.markdown('<h2 style="text-align:center;">Generating Project...</h2>', unsafe_allow_html=True)

    try:
        # Step 1: Generate Narrative
        narrative = project_generator._generate_scenario_narrative(
            st.session_state.sector_input,
            st.session_state.api_key,
            previous_context=history_context
        )

        if "error" in narrative:
            placeholder.empty()
            st.session_state['generation_error'] = narrative["error"]
            st.session_state.generation_phase = 'idle'
            st.rerun()
            return

        # Step 2: Generate Recipe
        definition = project_generator._generate_data_recipe(narrative, st.session_state.api_key)

        if "error" in definition:
            placeholder.empty()
            st.session_state['generation_error'] = definition["error"]
            st.session_state.generation_phase = 'idle'
            st.rerun()
            return

        # Generate Data
        if 'schema_list' in definition:
            # Inject granularity
            if 'dataset_granularity' not in definition and 'dataset_granularity' in narrative:
                definition['dataset_granularity'] = narrative['dataset_granularity']
            df = project_generator.generate_dataset(definition, rows=10000, apply_simulation_chaos=False)
        elif 'recipe' in definition:
            df = project_generator.generate_dataset(definition['recipe'], rows=10000, apply_simulation_chaos=False)
        else:
            placeholder.empty()
            st.session_state['generation_error'] = "Invalid recipe format received from AI."
            st.session_state.generation_phase = 'idle'
            st.rerun()
            return

        # Verify
        verification = verifier_service.verify_dataset_schema(
            definition,
            df,
            st.session_state.api_key
        )

        # Apply Chaos
        df = project_generator.apply_chaos_to_data(df, definition)

        # Clear Placeholder
        placeholder.empty()

        # Store Final Results
        st.session_state.verification_result = verification
        st.session_state.project = {
            "definition": definition,
            "data": df
        }

        # Update history
        new_history_item = f"{definition.get('title', '')} ({definition.get('recipe', {}).get('anchor_entity', {}).get('name', '')})"
        st.session_state.generated_history.append(new_history_item)

        # Put data in global session state
        st.session_state['project_data'] = df
        init_notebook_state()

        # Initialize chat
        st.session_state.messages = [{
            "role": "assistant",
            "content": f"Hello! I'm your Senior Data Analyst mentor. I've prepared a project for you on **{definition['title']}**. Check out the scenario and let me know if you need help!"
        }]

        # Set phase to complete
        st.session_state.generation_phase = 'complete'
        st.rerun()

    except Exception as e:
        placeholder.empty()
        st.session_state['generation_error'] = f"Error generating project: {e}"
        traceback.print_exc()
        st.session_state.generation_phase = 'idle'
        st.rerun()

def toggle_edit_mode(cell_id):
    current_state = st.session_state.cell_edit_state.get(cell_id, True)
    st.session_state.cell_edit_state[cell_id] = not current_state

def toggle_chat():
    st.session_state.chat_open = not st.session_state.chat_open

def send_chat_message():
    if st.session_state.chat_input_text:
        st.session_state.messages.append({"role": "user", "content": st.session_state.chat_input_text})
        st.session_state.chat_input_text = ""
        st.session_state.processing_chat = True

def start_generation_callback():
    if st.session_state.sector_input:
        if not st.session_state.api_key:
            st.toast("Starting in Mock Mode (No API Key detected)", icon="⚠️")
        st.session_state.generation_phase = 'generating'
    else:
        st.session_state['generation_error'] = "Please enter a sector."

def trigger_quick_start(sector_name):
    st.session_state.sector_input = sector_name
    start_generation_callback()

# --- UI Components ---

def get_python_completions():
    # ... (Same as before) ...
    return []

def get_sql_completions():
    # ... (Same as before) ...
    return []

def render_add_cell_controls(index):
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

    # 1. Launcher Button (Only visible if closed)
    if not st.session_state.chat_open:
        launcher = st.container()
        with launcher:
            # Styled orange circle button
            st.markdown("""
            <style>
            div[data-testid="stButton"] button.chat-launcher {
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background-color: var(--accent-orange) !important;
                color: white !important;
                box-shadow: 0 4px 10px rgba(0,0,0,0.3);
                border: none;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            </style>
            """, unsafe_allow_html=True)
            if st.button("💬", key="chat_launcher"):
                toggle_chat()
                st.rerun()
        launcher.float("bottom: 2rem; right: 2rem; position: fixed; z-index: 9999;")

    # 2. Open Chat Window
    else:
        chat_window = st.container()
        with chat_window:
            # Card styling applied via container wrapper below
            with st.container(border=True):
                # Header
                c_head, c_close = st.columns([8, 1])
                with c_head:
                    st.markdown("**✨ AI Mentor**")
                with c_close:
                    if st.button("✕", key="close_chat"):
                        toggle_chat()
                        st.rerun()

                # Messages
                chat_msgs = st.container(height=300)
                for msg in st.session_state.messages:
                    with chat_msgs.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else None):
                        st.write(msg["content"])

                # Input
                st.text_input("Ask a question...", key="chat_input_text", on_change=send_chat_message)

                # Process
                if st.session_state.processing_chat:
                    with st.spinner("Thinking..."):
                        try:
                            # Construct context
                            project_context = {
                                'title': definition.get('title'),
                                'description': definition.get('description'),
                                'tasks': definition.get('tasks'),
                                'display_schema': definition.get('display_schema', definition.get('schema_list'))
                            }

                            code_context = {
                                "notebook": [
                                    {
                                        "cell_type": cell['type'],
                                        "source": cell['content'],
                                        "output": cell.get('output', '')
                                    } for cell in st.session_state.notebook_cells
                                ]
                            }

                            response = llm_service.generate_text(
                                prompt=st.session_state.messages[-1]["content"],
                                api_key=st.session_state.api_key,
                                project_context=project_context,
                                code_context=code_context,
                                history=st.session_state.messages
                            )
                        except Exception as e:
                            response = f"I'm having trouble connecting. Error: {e}"

                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.session_state.processing_chat = False
                        st.rerun()

        chat_window.float("bottom: 2rem; right: 2rem; width: 350px; background-color: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color); z-index: 9999;")

def render_notebook():
    render_add_cell_controls(0)

    for idx, cell in enumerate(st.session_state.notebook_cells):
        cell_key = f"cell_{cell['id']}"

        # Header Info
        if cell['type'] == 'markdown':
            icon, title = "📝", "MARKDOWN BLOCK"
        elif cell['type'] == 'code':
            icon, title = "🐍", "CODE BLOCK"
        else:
            icon, title = "🗄️", "SQL BLOCK"

        # --- Card Structure using Negative Margins ---
        with st.container(border=True):
            # 1. Negative Margin Header
            st.markdown(f'''
                <div class="card-header-wrapper">
                    <div class="card-header-title">{icon} {title}</div>
                    <!-- Place for controls if we could put buttons here, but we can't easily -->
                </div>
            ''', unsafe_allow_html=True)

            # 2. Controls (Visual alignment below header)
            # We move the delete button to be "floating" top right or just in a row below
            # To make it look like it's in the header, we'd need more hacks.
            # For now, we put it in a right-aligned row immediately below the header.

            c_spacer, c_actions = st.columns([1, 0.1])
            with c_actions:
               if st.button("🗑️", key=f"del_{cell_key}"):
                   delete_cell(idx)

            st.divider() # distinct separation

            # Content
            if cell['type'] == 'markdown':
                is_editing = st.session_state.cell_edit_state.get(cell['id'], True)
                if is_editing:
                    st_quill(value=cell['content'], key=f"quill_{cell_key}")
                    if st.button("Done", key=f"save_{cell_key}"):
                        toggle_edit_mode(cell['id'])
                        st.rerun()
                else:
                    st.markdown(cell['content'], unsafe_allow_html=True)
                    if st.button("Edit", key=f"edit_{cell_key}"):
                        toggle_edit_mode(cell['id'])
                        st.rerun()

            elif cell['type'] == 'code':
                # Custom Run Button Styling for CodeEditor
                btn_css = """
                background-color: #238636;
                color: white;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                padding: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                """
                response = code_editor(
                    cell['content'],
                    lang="python",
                    key=f"ce_{cell_key}",
                    buttons=[{
                        "name": "Run",
                        "feather": "Play",
                        "primary": True,
                        "hasText": False,
                        "style": {"backgroundColor": "#238636", "borderRadius": "50%", "width": "24px", "height": "24px", "padding": "4px", "color": "white", "top": "-35px", "right": "5px"}
                        # Positioning hack to move button to header?
                        # No, code editor buttons are inside the iframe.
                        # We'll put it in the top right of the editor.
                    }]
                )
                if response['type'] == "submit" and response['text']:
                    st.session_state.notebook_cells[idx]['content'] = response['text']
                    execute_cell(idx)
                    st.rerun()

                if cell.get('output'):
                    st.code(cell['output'])
                if cell.get('result') is not None:
                    st.write(cell['result'])

        render_add_cell_controls(idx + 1)

def render_sidebar():
    if st.session_state.project:
        definition = st.session_state.project['definition']
        with st.sidebar:
            st.markdown('<div class="mission-hub-header">MISSION HUB</div>', unsafe_allow_html=True)
            st.markdown('<div class="mission-scope">ANALYTICAL SCOPE</div>', unsafe_allow_html=True)

            st.markdown('<div class="mission-sub">📄 THE NARRATIVE</div>', unsafe_allow_html=True)
            st.subheader(definition.get('title', 'Project'))
            st.markdown(definition.get('description', ''), unsafe_allow_html=True)

            st.markdown('<div class="mission-sub">🎯 OBJECTIVES</div>', unsafe_allow_html=True)
            for t in definition.get('tasks', []):
                st.markdown(f"- {t}")

            st.divider()
            # Push to bottom using spacer? Streamlit sidebar doesn't support flex spacer easily.
            # We just place it at the end.
            st.markdown('<div class="mission-sub">DATA ASSETS</div>', unsafe_allow_html=True)

            # Serialize session for export
            try:
                session_json = serialize_session({
                    'project': st.session_state.project,
                    'notebook_cells': st.session_state.notebook_cells,
                    'messages': st.session_state.messages,
                    'generated_history': st.session_state.generated_history,
                    'project_data': st.session_state.project_data
                })
                st.download_button(
                    label="Export Portfolio Session",
                    data=session_json,
                    file_name=f"data_forge_session_{int(pd.Timestamp.now().timestamp())}.json",
                    mime="application/json",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Export failed: {e}")

def render_data_explorer():
    st.info("Data Explorer - Coming Soon")
    st.dataframe(st.session_state.project['data'].head(50))

def render_workspace():
    # Render Sidebar
    render_sidebar()

    # Top Bar
    c_nav, c_status = st.columns([1, 1])
    with c_nav:
        mode = st.radio("Mode", ["Notebook", "Data Explorer"], horizontal=True, label_visibility="collapsed", key="nav_radio")
        st.session_state.active_tab = mode

    with c_status:
        st.markdown("""
        <div style="text-align: right; margin-top: 5px;">
            <span class="workspace-status"><span class="status-dot"></span> LOCAL KERNEL ACTIVE</span>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    if st.session_state.active_tab == "Notebook":
        render_notebook()
    else:
        render_data_explorer()

    render_floating_chat()

def render_landing():
    c_title, c_settings = st.columns([5, 1])
    with c_title:
        st.title("Data Forge")
    with c_settings:
        with st.popover("⚙️ Settings", use_container_width=True):
            st.text_input("Gemini API Key", key="api_key", type="password", help="Leave empty for Mock Mode")
            st.divider()
            st.file_uploader("Restore Session", type=["json"], key="session_uploader", on_change=load_session_callback)

    st.text_input("Sector", key="sector_input", on_change=start_generation_callback)

    # Render Quick Start Buttons
    cols = st.columns(4)
    quick_starts = [
        ("🛍️ Retail", "Retail"),
        ("🏥 Healthcare", "Healthcare"),
        ("💰 Finance", "Finance"),
        ("💻 Tech", "Technology")
    ]

    for i, (label, value) in enumerate(quick_starts):
        with cols[i]:
            st.button(label, use_container_width=True, on_click=trigger_quick_start, args=(value,))


# --- Run ---
if st.session_state.generation_phase == 'generating':
    render_loading_screen(st.empty())
elif st.session_state.project is None:
    render_landing()
else:
    render_workspace()
