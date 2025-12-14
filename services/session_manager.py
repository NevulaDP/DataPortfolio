import json
import pandas as pd
import io

def serialize_session(session_state):
    """
    Serializes the current session state into a JSON string.
    Handles the pandas DataFrame separately to ensure robust serialization.
    """
    # Create a safe copy of the project dictionary without the DataFrame object
    project_snapshot = session_state.get("project")
    project_safe = None
    if project_snapshot:
        project_safe = project_snapshot.copy()
        # Remove the 'data' key which holds the DataFrame object
        if "data" in project_safe:
            del project_safe["data"]

    # Sanitize notebook cells to remove non-serializable 'result' objects
    raw_cells = session_state.get("notebook_cells", [])
    safe_cells = []
    for cell in raw_cells:
        cell_copy = cell.copy()
        # 'result' often contains DataFrames, Figures, etc.
        # We strip it for serialization. On load, users will need to run cells to see results.
        if "result" in cell_copy:
            cell_copy["result"] = None
        safe_cells.append(cell_copy)

    data = {
        "project": project_safe,
        "notebook_cells": safe_cells,
        "messages": session_state.get("messages", []),
        "generated_history": session_state.get("generated_history", []),
    }

    # Serialize DataFrame separately
    df = session_state.get("project_data")
    if df is not None:
        try:
            # usage of orient='split' preserves index and column types better
            data["project_data"] = df.to_json(orient="split", date_format="iso")
        except Exception as e:
            print(f"Error serializing dataframe: {e}")
            data["project_data"] = None
    else:
        data["project_data"] = None

    return json.dumps(data, indent=2)

def deserialize_session(json_content):
    """
    Deserializes a JSON string back into session state objects.
    Returns a dictionary of state components to update.
    """
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError:
        return None

    result = {
        "project": data.get("project"),
        "notebook_cells": data.get("notebook_cells", []),
        "messages": data.get("messages", []),
        "generated_history": data.get("generated_history", [])
    }

    # Reconstruct DataFrame
    df_json = data.get("project_data")
    if df_json:
        try:
            # We use io.StringIO because read_json expects a string or file-like object
            df = pd.read_json(io.StringIO(df_json), orient="split")
            result["project_data"] = df

            # Re-attach the dataframe to the project dictionary if it exists
            if result["project"] and isinstance(result["project"], dict):
                 result["project"]["data"] = df

        except Exception as e:
            print(f"Error deserializing dataframe: {e}")
            result["project_data"] = None
    else:
        result["project_data"] = None

    return result
