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

        # Handle Schema-First vs Legacy
        if 'schema_list' in project_definition:
            # For new format, schema_list IS the display schema
            display_schema = project_definition.get('schema_list', [])
        else:
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

        **CRITICAL INSTRUCTION - IGNORE INTENTIONAL MESSINESS:**
        This is a dataset for a *Junior Analyst Portfolio Project*. It is *supposed* to be imperfect.
        - **IGNORE** Logical Flaws (e.g., "Install date after Login date", "Negative duration"). This is for the analyst to clean.
        - **IGNORE** Dirty Data / Outliers (e.g., "Country" column has some random strings or nulls). This is for the analyst to clean.
        - **IGNORE** Format Inconsistencies (e.g., Dates as strings).

        **FOCUS ONLY ON BLOCKERS:**
        1. **Critical Type Mismatches:** (e.g., Schema says "String/Name" but data is strictly "True/False" booleans). This is a FAIL.
        2. **Missing Columns:** If a column required for a task is missing. This is a FAIL.
        3. **Total Garbage:** If the column contains data that is *completely* unusable for the intended task (e.g. "Revenue" column containing only names).

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
