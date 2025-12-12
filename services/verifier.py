from .llm import LLMService
import pandas as pd
import json

class VerifierService:
    def __init__(self):
        self.llm_service = LLMService()

    def verify_dataset_schema(self, project_definition: dict, df: pd.DataFrame, api_key: str) -> dict:
        """
        Verifies if the generated dataset fits the scenario, tasks, and schema description.
        Returns a JSON report.
        """
        if df is None or df.empty:
            return {"valid": False, "issues": ["Dataset is empty."], "score": 0}

        # Prepare context
        title = project_definition.get('title', 'N/A')
        description = project_definition.get('description', 'N/A')
        tasks = project_definition.get('tasks', [])
        display_schema = project_definition.get('display_schema', [])

        # Data Sample
        sample_head = df.head(5).to_string(index=False)
        dtypes = df.dtypes.to_string()

        prompt = f"""
        Act as a Data Quality Auditor.
        You are verifying a synthetic dataset generated for a specific Data Analysis Project.

        **Project Scenario:**
        Title: {title}
        Description: {description}

        **Tasks the User Must Solve:**
        {json.dumps(tasks, indent=2)}

        **Expected Schema (What the user was told):**
        {json.dumps(display_schema, indent=2)}

        **Actual Data Sample (First 5 rows):**
        {sample_head}

        **Actual Data Types:**
        {dtypes}

        **Your Goal:**
        Verify if the **Actual Data** matches the **Expected Schema** and is sufficient to solve the **Tasks**.

        Specific Checks:
        1. **Type Mismatches:** Does the column content match the description? (e.g., If description says "User's full name" but data is "True/False", that is a FAIL).
        2. **Task Feasibility:** Do the columns needed for the tasks exist and contain usable data?
        3. **Consistency:** Does the data look relevant to the scenario?

        Output a valid JSON object:
        {{
            "valid": true/false,  // Set to false if there are CRITICAL blockers (wrong types for core tasks).
            "score": 0-100,       // Quality score.
            "issues": [           // List of strings describing specific problems. Empty if perfect.
                "Column 'x' is boolean but schema says 'City Name'.",
                "Task requires calculating 'revenue' but no price column exists."
            ]
        }}
        """

        return self.llm_service.generate_json(prompt, api_key, temperature=0.1)
