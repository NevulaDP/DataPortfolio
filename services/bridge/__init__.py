import os
import streamlit.components.v1 as components

# Create a _release component
# In development, we can point to a dev server, but for this task we will point to the static HTML we just created.
# Since Streamlit Components require serving static files, we declare the path.

_component_func = components.declare_component(
    "execution_bridge",
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
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
