import os
import streamlit.components.v1 as components

# Create a _RELEASE constant. We'll set it to True since we aren't running a dev server for the component.
_RELEASE = True

if not _RELEASE:
    # Development mode: use `npm run start` and point to localhost
    # (Not used in this plan, keeping standard structure)
    _component_func = components.declare_component(
        "execution_bridge",
        url="http://localhost:3001",
    )
else:
    # Production mode: point to the build directory (or raw html file)
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(parent_dir, "frontend")
    _component_func = components.declare_component(
        "execution_bridge",
        path=frontend_dir
    )

def execution_bridge(cmd, data=None, code=None, cell_id=None, cell_type="code", key=None):
    """
    Component to bridge Streamlit and Pyodide.

    Args:
        cmd (str): 'load_data' or 'execute'
        data (str): CSV string of the dataframe (only for load_data)
        code (str): Source code to run
        cell_id (str): Unique ID for the execution request
        cell_type (str): 'code' (python) or 'sql'
        key (str): Streamlit unique key
    """
    return _component_func(
        cmd=cmd,
        data=data,
        code=code,
        id=cell_id,
        cell_type=cell_type,
        key=key,
        default=None
    )
