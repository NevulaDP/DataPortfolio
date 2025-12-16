import os
import streamlit.components.v1 as components

# Create a _RELEASE constant.
_RELEASE = True

def execution_bridge(cmd, data=None, code=None, cell_id=None, cell_type="code", key=None):
    """
    Component to bridge Streamlit and Pyodide.
    """

    # Calculate path
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(parent_dir, "frontend")

    # Debug: Check if index.html exists
    index_path = os.path.join(frontend_dir, "index.html")
    if not os.path.exists(index_path):
        # Fallback error
        return None

    # Declare component
    # We declare it here to ensure the path is resolved at runtime correctly
    _component_func = components.declare_component(
        "execution_bridge_v1",
        path=frontend_dir
    )

    return _component_func(
        cmd=cmd,
        data=data,
        code=code,
        id=cell_id,
        cell_type=cell_type,
        key=key,
        default=None
    )
