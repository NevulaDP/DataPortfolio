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
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stButton button {
        border-radius: 24px;
    }

    /* Enhanced Loader */
    .loading-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 70vh; /* Occupy most of the screen */
        width: 100%;
    }

    /* CSS Variables for Colors (Default to Dark) */
    :root {
        --loader-c1: #0F1864;
        --loader-c2: #271781;
        --loader-c3: #317295;
        --loader-c4: #F29B3B;
        --loader-c5: #FF8080;
    }

    /* Light Mode Overrides */
    body.st-theme-light {
        --loader-c1: #1E30C2;
        --loader-c2: #4A33D6;
        --loader-c3: #3E94C0;
        --loader-c4: #F29B3B;
        --loader-c5: #FF8080;
    }

    /* Wrapper for the Loader */
    .loader {
        position: relative;
        width: 100px;
        height: 100px;
    }

    /* The Rotating Container (The Window/Mask) */
    .loader .spinner {
        position: absolute;
        inset: 0;
        animation: spin 1.2s linear infinite;

        /* The Comet Tail Mask */
        mask: conic-gradient(from 0deg, transparent 50%, black 100%);
        -webkit-mask: conic-gradient(from 0deg, transparent 50%, black 100%);
    }

    /* Shared Ring Styles (Static Colors, Counter-Rotating) */
    .loader .spinner .ring {
        position: absolute;
        inset: 10px; /* 100px - 20px = 80px ring size */
        border-radius: 50%;

        /* Full Spectrum Gradient Loop */
        background: conic-gradient(
            from 0deg,
            var(--loader-c1),
            var(--loader-c2),
            var(--loader-c3),
            var(--loader-c4),
            var(--loader-c5),
            var(--loader-c1)
        );

        /* The Hole */
        mask: radial-gradient(farthest-side, transparent calc(100% - 8px), #fff calc(100% - 8px + 1px));
        -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 8px), #fff calc(100% - 8px + 1px));

        /* Counter-Rotation to keep colors static */
        animation: spin-reverse 1.2s linear infinite;
    }

    .loader .spinner .ring.glow {
        filter: blur(8px);
        opacity: 0.8;
        z-index: 1;
    }

    .loader .spinner .ring.main {
        z-index: 3;
    }

    /* Unmasked Cap Container (Sibling to Spinner) */
    .loader .cap-container {
        position: absolute;
        inset: 0;
        animation: spin 1.2s linear infinite; /* Synced rotation */
    }

    /* The Round Cap Circle */
    .loader .cap-container .cap {
        position: absolute;
        top: 10px; /* Matches inset of ring */
        left: 50%;
        width: 8px;
        height: 8px;
        transform: translateX(-50%);
        border-radius: 50%;
        overflow: hidden;
    }

    .loader .cap-container.glow {
        filter: blur(8px);
        opacity: 0.8;
        z-index: 2;
    }

    .loader .cap-container.main {
        z-index: 4;
    }

    /* The Cap's Inner Gradient (Counter-Rotating) */
    .loader .cap-container .cap .cap-inner {
        position: absolute;
        width: 80px; /* Ring Size */
        height: 80px;
        top: -4px; /* Offset to align center */
        left: -36px;

        background: conic-gradient(
            from 0deg,
            var(--loader-c1),
            var(--loader-c2),
            var(--loader-c3),
            var(--loader-c4),
            var(--loader-c5),
            var(--loader-c1)
        );

        animation: spin-reverse 1.2s linear infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    @keyframes spin-reverse {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(-360deg); }
    }

    /* Pulsing Text */
    .loading-text {
        margin-top: 30px;
        font-size: 24px;
        font-weight: 600;
        color: var(--text-color);
        font-family: 'Source Sans Pro', sans-serif;
        animation: pulse-text 1.5s ease-in-out infinite;
    }

    @keyframes pulse-text {
        0% { opacity: 0.6; }
        50% { opacity: 1; }
        100% { opacity: 0.6; }
    }

    /* Dark Mode Support for st_quill */
    /* Target body with class added by JS injection */
    body.st-theme-dark iframe[title="streamlit_quill.streamlit_quill"] {
        filter: invert(1) hue-rotate(180deg);
    }

    /* --- New Branding Styles --- */

    /* Buttons: Gradient Styling (Default / Dark Mode) */
    div.stButton > button {
        background: linear-gradient(90deg, var(--loader-c4) 0%, var(--loader-c5) 100%);
        color: white !important;
        border: none;
        padding: 0.5rem 0.75rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        white-space: nowrap;
    }

    div.stButton > button:hover {
        box-shadow: 0 0 12px var(--loader-c5); /* Glow effect */
        color: white !important;
    }

    /* Buttons: Light Mode Overrides */
    body.st-theme-light div.stButton > button {
        background: linear-gradient(90deg, var(--loader-c1) 0%, var(--loader-c2) 100%);
    }

    body.st-theme-light div.stButton > button:hover {
        box-shadow: 0 0 12px var(--loader-c2); /* Glow effect */
    }

    div.stButton > button:active {
        transform: translateY(0);
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Headers: Gradient Text */
    /* Default (Dark Mode) - Bright Warm Colors */
    h1, h2, h3 {
        background: linear-gradient(90deg, var(--loader-c4), var(--loader-c5));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        color: transparent;
        width: fit-content; /* Ensure gradient doesn't stretch full width if not needed */
    }

    /* Light Mode - Deep Cool Colors */
    body.st-theme-light h1,
    body.st-theme-light h2,
    body.st-theme-light h3 {
        background: linear-gradient(90deg, var(--loader-c1), var(--loader-c2));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        color: transparent;
    }

    /* --- Landing Page Specifics --- */
    .landing-header {
        font-size: 3.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        background: linear-gradient(90deg, var(--loader-c4), var(--loader-c5));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: left;
        line-height: 1.2;
    }

    body.st-theme-light .landing-header {
        background: linear-gradient(90deg, var(--loader-c1), var(--loader-c2));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .landing-sub {
        font-size: 3rem;
        color: var(--text-color);
        margin-bottom: 3rem;
        font-weight: 600;
        text-align: left;
        line-height: 1.2;
        opacity: 0.9;
    }

    /* Style the input to look like the Gemini bar */
    .stTextInput input {
        border-radius: 24px !important;
        padding: 1.5rem 1.5rem !important;
        font-size: 1.1rem !important;
        background-color: #1e1e1e; /* Dark gray */
        border: 1px solid #333;
    }
    body.st-theme-light .stTextInput input {
        background-color: #f0f2f6;
        border: 1px solid #ddd;
    }

    .instruction-step {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        height: 100%;
    }
    body.st-theme-light .instruction-step {
        background: rgba(0, 0, 0, 0.03);
        border: 1px solid rgba(0, 0, 0, 0.05);
    }

</style>
""", unsafe_allow_html=True)

# Inject JS to detect theme based on computed background color
import streamlit.components.v1 as components
components.html("""
<script>
    function checkTheme() {
        try {
            // Access parent document (main app)
            const parentDoc = window.parent.document;
            const body = parentDoc.body;

            // Get computed background color of the body or main container
            // Streamlit applies theme to .stApp or body
            const computedStyle = window.parent.getComputedStyle(body);
            const bgColor = computedStyle.backgroundColor;

            // Check if color is dark
            // RGB(r, g, b)
            const rgb = bgColor.match(/\d+/g);
            if (rgb) {
                const r = parseInt(rgb[0]);
                const g = parseInt(rgb[1]);
                const b = parseInt(rgb[2]);

                // Simple brightness formula
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

    // Run periodically to catch theme toggles
    setInterval(checkTheme, 500);
    checkTheme(); // Initial check
</script>
""", height=0, width=0)

# --- Functions ---

def load_session_callback():
    uploaded_file = st.session_state.get('session_uploader')
    if uploaded_file is not None:
        try:
            # Read string content
            content = uploaded_file.getvalue().decode("utf-8")
            new_state = deserialize_session(content)

            if new_state:
                st.session_state.project = new_state['project']
                st.session_state.notebook_cells = new_state['notebook_cells']
                st.session_state.messages = new_state['messages']
                st.session_state.generated_history = new_state['generated_history']
                st.session_state.project_data = new_state['project_data']

                # Re-init notebook scope
                init_notebook_state()

                st.toast("Session loaded successfully!", icon="✅")
            else:
                st.error("Failed to parse session file.")
        except Exception as e:
            st.error(f"Error loading session: {e}")

def init_notebook_state():
    # Initialize scope with user data only (modules are injected at execution time)
    # We only store variables that need persistence (like df, user vars)
    st.session_state.notebook_scope = {
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

def get_execution_scope():
    """
    Constructs the execution scope by merging the persistent user scope
    with standard library modules. This prevents modules from being stored
    in session state (which causes pickling errors).
    """
    # Base scope from user session
    scope = st.session_state.notebook_scope.copy()

    # Inject modules
    scope.update({
        'pd': pd,
        'np': np,
        'plt': plt,
        'sns': sns,
        'st': st,
    })
    return scope

def update_persistent_scope(exec_scope):
    """
    Updates the persistent session state with new variables from execution,
    excluding the auto-injected modules. Handles additions, updates, and deletions.
    """
    # Keys to exclude from persistence (because they are auto-injected)
    EXCLUDED_KEYS = {'pd', 'np', 'plt', 'sns', 'st'}

    # 1. Update/Add new variables
    for key, val in exec_scope.items():
        if key.startswith('_'): continue
        if key in EXCLUDED_KEYS: continue

        st.session_state.notebook_scope[key] = val

    # 2. Handle Deletions
    # If a key exists in persistent scope but is missing from exec_scope, it was deleted.
    # Note: We must operate on a list of keys to avoid RuntimeError during modification.
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

        # Get fresh scope
        exec_scope = get_execution_scope()

        try:
            with contextlib.redirect_stdout(output_buffer):
                # Parse code to handle last expression
                try:
                    tree = ast.parse(code)
                except SyntaxError:
                    # If syntax error, just let exec fail
                    exec(code, exec_scope)
                    tree = None

                if tree and tree.body:
                    last_node = tree.body[-1]
                    if isinstance(last_node, ast.Expr):
                        # Compile and exec everything before the last expression
                        if len(tree.body) > 1:
                            module = ast.Module(body=tree.body[:-1], type_ignores=[])
                            exec(compile(module, filename="<string>", mode="exec"), exec_scope)

                        # Eval the last expression
                        expr = ast.Expression(body=last_node.value)
                        result_obj = eval(compile(expr, filename="<string>", mode="eval"), exec_scope)
                    else:
                        # No expression at end, just exec all
                        exec(code, exec_scope)
                elif tree is None:
                    pass # Already executed in except block
                else:
                    # Empty code
                    pass

            # Persist changes back to session state
            update_persistent_scope(exec_scope)

            st.session_state.notebook_cells[cell_idx]['output'] = output_buffer.getvalue()
            st.session_state.notebook_cells[cell_idx]['result'] = result_obj

        except Exception as e:
            # Catch all exceptions to prevent app crash
            st.session_state.notebook_cells[cell_idx]['output'] = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            st.session_state.notebook_cells[cell_idx]['result'] = None

    elif cell_type == 'sql':
        try:
            # Connect to DuckDB
            con = duckdb.connect()

            # Get Python Scope
            exec_scope = get_execution_scope()

            # Register all DataFrames and Series found in the scope
            for var_name, var_val in exec_scope.items():
                if isinstance(var_val, pd.DataFrame):
                    try:
                        con.register(var_name, var_val)
                        # Also register 'data' if it's the main df
                        if var_name == 'df':
                            con.register('data', var_val)
                    except Exception:
                        pass # Ignore registration errors
                elif isinstance(var_val, pd.Series):
                    try:
                        # DuckDB requires DataFrame for registration
                        con.register(var_name, var_val.to_frame())
                    except Exception:
                        pass # Ignore registration errors

            try:
                # Execute Query and return as DataFrame
                result_df = con.execute(code).df()

                # Save result to Python scope
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

def render_loading_screen(placeholder):
    try:
        # Pass history to prevent repetition
        history_context = st.session_state.generated_history[-5:] # Keep last 5 context items

        # Step 1: Generate Narrative (Fixed)
        placeholder.markdown('''
            <div class="loading-container">
                <div class="loader">
                    <div class="spinner">
                        <div class="ring glow"></div>
                        <div class="ring main"></div>
                    </div>
                    <div class="cap-container glow">
                        <div class="cap"><div class="cap-inner"></div></div>
                    </div>
                    <div class="cap-container main">
                        <div class="cap"><div class="cap-inner"></div></div>
                    </div>
                </div>
                <div class="loading-text">Drafting Scenario Narrative...</div>
            </div>
        ''', unsafe_allow_html=True)

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

        # Step 2: Generate Recipe & Data (Loop for correction)
        max_retries = 3
        current_try = 0
        definition = None
        df = None
        verification = None

        while current_try < max_retries:
            if current_try == 0:
                # Initial Recipe Generation
                placeholder.markdown('''
                    <div class="loading-container">
                        <div class="loader">
                            <div class="spinner">
                                <div class="ring glow"></div>
                                <div class="ring main"></div>
                            </div>
                            <div class="cap-container glow">
                                <div class="cap"><div class="cap-inner"></div></div>
                            </div>
                            <div class="cap-container main">
                                <div class="cap"><div class="cap-inner"></div></div>
                            </div>
                        </div>
                        <div class="loading-text">Designing Data Recipe...</div>
                    </div>
                ''', unsafe_allow_html=True)
                definition = project_generator._generate_data_recipe(narrative, st.session_state.api_key)
            else:
                # Refinement based on feedback
                placeholder.markdown(f'''
                    <div class="loading-container">
                        <div class="loader">
                            <div class="spinner">
                                <div class="ring glow"></div>
                                <div class="ring main"></div>
                            </div>
                            <div class="cap-container glow">
                                <div class="cap"><div class="cap-inner"></div></div>
                            </div>
                            <div class="cap-container main">
                                <div class="cap"><div class="cap-inner"></div></div>
                            </div>
                        </div>
                        <div class="loading-text">Refining data (Attempt {current_try+1})...</div>
                    </div>
                ''', unsafe_allow_html=True)
                definition = project_generator.refine_data_recipe(
                    narrative,
                    verification['issues'],
                    st.session_state.api_key
                )

            if "error" in definition:
                placeholder.empty()
                st.session_state['generation_error'] = definition["error"]
                st.session_state.generation_phase = 'idle'
                st.rerun()
                return

            # Handle new "Schema-First" format (schema_list at root) vs Legacy (recipe key)
            if 'schema_list' in definition:
                # Inject granularity manually if missing from LLM output but present in narrative
                if 'dataset_granularity' not in definition and 'dataset_granularity' in narrative:
                    definition['dataset_granularity'] = narrative['dataset_granularity']
                placeholder.markdown('''
                    <div class="loading-container">
                        <div class="loader">
                            <div class="spinner">
                                <div class="ring glow"></div>
                                <div class="ring main"></div>
                            </div>
                            <div class="cap-container glow">
                                <div class="cap"><div class="cap-inner"></div></div>
                            </div>
                            <div class="cap-container main">
                                <div class="cap"><div class="cap-inner"></div></div>
                            </div>
                        </div>
                        <div class="loading-text">Generating Synthetic Data...</div>
                    </div>
                ''', unsafe_allow_html=True)
                df = project_generator.generate_dataset(definition, rows=10000)
            elif 'recipe' in definition:
                # Legacy fallback
                placeholder.markdown('''
                    <div class="loading-container">
                        <div class="loader">
                            <div class="spinner">
                                <div class="ring glow"></div>
                                <div class="ring main"></div>
                            </div>
                            <div class="cap-container glow">
                                <div class="cap"><div class="cap-inner"></div></div>
                            </div>
                            <div class="cap-container main">
                                <div class="cap"><div class="cap-inner"></div></div>
                            </div>
                        </div>
                        <div class="loading-text">Generating Synthetic Data...</div>
                    </div>
                ''', unsafe_allow_html=True)
                df = project_generator.generate_dataset(definition['recipe'], rows=10000)
            else:
                placeholder.empty()
                st.session_state['generation_error'] = "Invalid recipe format received from AI."
                st.session_state.generation_phase = 'idle'
                st.rerun()
                return

            # Verify
            placeholder.markdown('''
                <div class="loading-container">
                    <div class="loader">
                        <div class="spinner">
                            <div class="ring glow"></div>
                            <div class="ring main"></div>
                        </div>
                        <div class="cap-container glow">
                            <div class="cap"><div class="cap-inner"></div></div>
                        </div>
                        <div class="cap-container main">
                            <div class="cap"><div class="cap-inner"></div></div>
                        </div>
                    </div>
                    <div class="loading-text">Verifying Data Quality...</div>
                </div>
            ''', unsafe_allow_html=True)
            verification = verifier_service.verify_dataset_schema(
                definition,
                df,
                st.session_state.api_key
            )

            # Check Validity
            if verification.get('valid', True):
                break # Success!

            current_try += 1

        # Clear Pulse
        placeholder.empty()

        # Store Final Results (even if invalid after max retries)
        st.session_state.verification_result = verification
        st.session_state.project = {
            "definition": definition,
            "data": df
        }

        # Update history with the new project title and anchor
        new_history_item = f"{definition.get('title', '')} ({definition.get('recipe', {}).get('anchor_entity', {}).get('name', '')})"
        st.session_state.generated_history.append(new_history_item)

        # Put data in global session state and scope
        st.session_state['project_data'] = df
        init_notebook_state()

        # Initialize chat
        st.session_state.messages = [{
            "role": "assistant",
            "content": f"Hello! I'm your Senior Data Analyst mentor. I've prepared a project for you on **{definition['title']}**. Check out the scenario and let me know if you need help!"
        }]

        # Set phase to complete to trigger workspace render on next run
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
    # Positioned on the right side (independent of sidebar)
    # Uses 'canvas' background to ensure opacity and adaptation to system/browser theme
    # Raised bottom offset to clear Streamlit footer
    chat_con.float("bottom: 5rem; right: 3rem; width: 400px; z-index: 99999; background-color: canvas !important; color: var(--text-color); border-radius: 10px;")


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
    # Only render sidebar when in workspace mode
    if st.session_state.project is not None:
        with st.sidebar:
            # Display Logo if present
            if os.path.exists("logo.png"):
                # Center the logo using columns
                _, col_logo, _ = st.columns([1, 1, 1])
                with col_logo:
                    st.image("logo.png", width=150)

            st.title("Settings")
            # API Key is also here for persistent access
            st.text_input(
                "Gemini API Key",
                type="password",
                help="Enter your Google Gemini API Key. It is used only for this session and not stored.",
                key="api_key_sidebar",
                value=st.session_state.api_key,
                on_change=lambda: st.session_state.update({"api_key": st.session_state.api_key_sidebar})
            )

            if st.session_state.api_key:
                st.success("API Key configured.")
            else:
                st.warning("No API Key set. Using Mock Mode.")

            st.divider()

            # Save Session (Only in Workspace)
            st.subheader("Save Session")
            try:
                # Serialize current state
                json_str = serialize_session(st.session_state)
                st.download_button(
                    "💾 Download Session",
                    data=json_str,
                    file_name="analysis_session.json",
                    mime="application/json",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error preparing save: {e}")

def start_generation_callback():
    if st.session_state.sector_input:
        # Check for API Key if not present
        if not st.session_state.api_key:
            # We allow it (Mock Mode), but we could block it if required.
            # The prompt says "prompt the user... because it is mandatory", but we have a mock mode.
            # I'll stick to allowing it but maybe showing a toast.
            st.toast("Starting in Mock Mode (No API Key detected)", icon="⚠️")

        st.session_state.generation_phase = 'generating'
    else:
        st.session_state['generation_error'] = "Please enter a sector."

def trigger_quick_start(sector_name):
    st.session_state.sector_input = sector_name
    start_generation_callback()
    st.rerun()

def render_landing():
    # Centered Layout
    c_spacer_l, c_main, c_spacer_r = st.columns([1, 6, 1])

    with c_main:
        # Headers
        st.markdown('<div class="landing-header">Hi Analyst</div>', unsafe_allow_html=True)
        st.markdown('<div class="landing-sub">Where should we start?</div>', unsafe_allow_html=True)

        # Input & Settings Bar
        # We use a column layout to put the settings gear next to the input
        col_input, col_settings = st.columns([8, 1], gap="small")

        with col_input:
            st.text_input(
                "Sector",
                placeholder="Enter a sector (e.g. Retail, Finance)...",
                key="sector_input",
                label_visibility="collapsed",
                on_change=start_generation_callback
            )

        with col_settings:
            # Settings Popover
            with st.popover("⚙️", use_container_width=True, help="Settings (API Key & Restore)"):
                st.markdown("### Settings")

                # API Key Input (synced with session state)
                new_key = st.text_input(
                    "Gemini API Key",
                    type="password",
                    value=st.session_state.api_key,
                    help="Enter your Google Gemini API Key.",
                    key="api_key_landing"
                )
                if new_key != st.session_state.api_key:
                    st.session_state.api_key = new_key
                    st.rerun()

                if st.session_state.api_key:
                    st.success("API Key set! ✅")
                else:
                    st.info("Enter key for custom projects. Leave empty for Mock Mode.")

                st.divider()
                st.markdown("### 📂 Restore Session")
                st.file_uploader(
                    "Upload .json file",
                    type=["json"],
                    key="session_uploader",
                    on_change=load_session_callback,
                    label_visibility="collapsed"
                )

        # Quick Start Pills
        st.markdown("") # Spacer
        cols = st.columns(4)
        quick_starts = [
            ("🛍️ Retail", "Retail"),
            ("🏥 Healthcare", "Healthcare"),
            ("💰 Finance", "Finance"),
            ("💻 Tech", "Technology")
        ]

        for i, (label, value) in enumerate(quick_starts):
            with cols[i]:
                if st.button(label, use_container_width=True):
                    trigger_quick_start(value)

        # Instructions / Context
        st.markdown("---")
        st.markdown("##### How it works")

        c_i1, c_i2, c_i3 = st.columns(3)
        with c_i1:
            st.markdown("""
            <div class="instruction-step">
                <h4>1. Pick a Sector</h4>
                <p style="opacity: 0.8; font-size: 0.9rem;">We'll generate a realistic business scenario and a messy dataset.</p>
            </div>
            """, unsafe_allow_html=True)
        with c_i2:
             st.markdown("""
            <div class="instruction-step">
                <h4>2. Analyze Data</h4>
                <p style="opacity: 0.8; font-size: 0.9rem;">Use the built-in Jupyter Notebook environment to clean and explore.</p>
            </div>
            """, unsafe_allow_html=True)
        with c_i3:
             st.markdown("""
            <div class="instruction-step">
                <h4>3. Get Mentorship</h4>
                <p style="opacity: 0.8; font-size: 0.9rem;">The AI Mentor guides your analysis and reviews your code.</p>
            </div>
            """, unsafe_allow_html=True)

        # Display error from previous failed generation if any
        if 'generation_error' in st.session_state:
            st.error(st.session_state.pop('generation_error'))

def render_workspace():
    project = st.session_state.project
    definition = project['definition']
    df = st.session_state.get('project_data')

    col_context, col_work = st.columns([1, 2], gap="large")

    # --- Context (Left Column) ---
    with col_context:
        st.subheader(definition['title'])
        st.markdown(f"<div style='text-align: justify; white-space: pre-wrap;'>{definition['description']}</div>", unsafe_allow_html=True)

        st.divider()
        st.caption(f"**Dataset Granularity:** {definition.get('dataset_granularity', 'Not specified')}")

        with st.expander("Tasks", expanded=True):
            for i, task in enumerate(definition['tasks']):
                st.write(f"{i+1}. {task}")

        with st.expander("Data Schema"):
            schema = definition.get('display_schema', definition.get('schema', definition.get('schema_list', [])))
            if schema:
                # Prepare data for display
                schema_data = []
                for col in schema:
                    schema_data.append({
                        "Column": col['name'],
                        "Type": col['type'],
                        "Description": col.get('description', '')
                    })

                st.dataframe(
                    schema_data,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Column": st.column_config.TextColumn("Column", width="small"),
                        "Type": st.column_config.TextColumn("Type", width="small"),
                        "Description": st.column_config.TextColumn("Description", width="large")
                    }
                )
            else:
                st.write("No schema information available.")

    # --- Notebook (Right Column) ---
    with col_work:
        st.title("Workspace")

        # Verification Alert has been hidden as per user request (logic still runs internally)
        # ver_res = st.session_state.get('verification_result')
        # ... (Hidden)

        if df is not None:
            # Data Preview
            st.subheader("Data Preview")
            st.dataframe(df.head(), use_container_width=True)

            # Download
            csv = df.to_csv(index=False).encode('utf-8')

            c_d1, c_d2 = st.columns([1, 1])
            with c_d1:
                st.download_button("Download Data", csv, "project_data.csv", "text/csv", use_container_width=True)
            with c_d2:
                # Generate Report
                html_report = generate_html_report(
                    definition['title'],
                    definition['description'],
                    st.session_state.notebook_cells
                )
                st.download_button(
                    "Download Report 📄",
                    html_report,
                    "project_report.html",
                    "text/html",
                    use_container_width=True,
                    help="To include a chart in the report, ensure the figure object (e.g., `fig`) is the last line of the cell."
                )

        st.divider()

        render_notebook()

    # --- Floating Chat ---
    render_floating_chat()

# --- Main App Logic ---

render_sidebar()

# Create a main placeholder to manage page transitions and ensure old content is cleared
main_placeholder = st.empty()

if st.session_state.generation_phase == 'generating':
    render_loading_screen(main_placeholder)
elif st.session_state.project is None:
    with main_placeholder.container():
        render_landing()
else:
    with main_placeholder.container():
        render_workspace()
