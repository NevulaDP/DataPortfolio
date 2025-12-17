import os
import streamlit.components.v1 as components
from pathlib import Path

# Create a _release component
# Point to the static HTML
frontend_dir = (Path(__file__).parent / "frontend").absolute()

_component_func = components.declare_component(
    "execution_bridge_v2",
    path=str(frontend_dir)
)

def execution_bridge(command=None, payload=None, key=None):
    """
    Component to bridge Streamlit and Pyodide.

    Args:
        command (str): "init_data", "execute_code", "execute_sql"
        payload (dict): Data to send (e.g. {code: "...", id: "..."} or {json_data: "..."})
    """
    component_value = _component_func(command=command, payload=payload, key=key, default=None)
    return component_value
