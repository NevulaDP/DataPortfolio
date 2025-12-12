import pandas as pd
import numpy as np
from faker import Faker
import random
import json
import re
from .llm import LLMService
from .chaos import ChaosToolkit

fake = Faker()
chaos = ChaosToolkit()
llm_service = LLMService()

class ProjectGenerator:
    def orchestrate_project_generation(self, sector: str, api_key: str = None, previous_context: list = None):
        """
        Orchestrates a 2-step generation process:
        1. Generate a creative scenario (Narrative).
        2. Generate a data recipe based on that narrative.
        """
        # Step 1: Generate Narrative
        narrative = self._generate_scenario_narrative(sector, api_key, previous_context)
        if "error" in narrative:
            return narrative

        # Step 2: Generate Data Recipe from Narrative
        full_project = self._generate_data_recipe(narrative, api_key)
        return full_project

    def _generate_scenario_narrative(self, sector: str, api_key: str, previous_context: list):
        random_seed = random.randint(1, 100000)

        # --- Structural Randomness to Force Variety ---

        # 1. Project Archetypes (Analysis Types)
        archetypes = [
            # General / Retail / Business
            "Sales Trend Analysis (identifying seasonal patterns and top performers)",
            "Customer Segmentation & Profiling (grouping users by behavior)",
            "Product Performance Review (analyzing sales vs returns)",
            "Customer Churn Analysis (identifying at-risk customers)",
            "Pricing & Discount Analysis (impact of discounts on revenue)",
            "Marketing & Acquisition Performance (ROI and conversion rates)",
            "Inventory Turnover & Stock Analysis (identifying slow-moving items)",
            "Operational KPI Dashboarding (tracking core business metrics)",

            # Tech / Digital
            "Product/Service Usage Trends (adoption and engagement metrics)",
            "A/B Test Result Analysis (comparing control vs variant groups)",
            "User Session & Behavior Analysis (time on site, drop-off points)",
            "Model/System Performance Analysis (Accuracy, Error Rates, Efficiency)", # Added for AI/Tech

            # Wildcards & Anomaly
            "Anomaly Detection (investigating data irregularities)",
            "Sector-Specific Operational Challenge (a unique problem relevant strictly to this industry)"
        ]

        # 2. Business Contexts (Scale/Stage)
        # Refined to be PURELY OPERATIONAL (No implied business models like 'SaaS' or 'Agency')
        contexts = [
            "A rapidly scaling high-growth startup",
            "A stable, family-owned business trying to modernize",
            "A large legacy corporation facing a PR crisis",
            "A non-profit organization struggling with resource allocation",
            "A company recently acquired by a larger firm", # New: Operational State
            "A company preparing for an IPO or major funding round", # New: Operational State
            "A company expanding into a new international market", # New: Operational State
            "A market leader facing stiff competition from a disruptor"
        ]

        # Select one Context randomly (this is safe to randomise)
        selected_context = random.choice(contexts)

        # For Archetypes, we provide the LIST to the LLM and let IT choose relevant vs random.
        archetypes_str = "\n".join([f"- {a}" for a in archetypes])

        avoid_str = ""
        if previous_context:
            avoid_str = "\n**FORBIDDEN TERMS (DO NOT USE):**\n" + ", ".join(previous_context) + "\n(You MUST generate a completely different company and scenario from these.)"

        prompt = f"""
        Act as an expert Creative Writer and Data Science Mentor.
        Create a unique, detailed, and realistic scenario for a Data Analysis project in the '{sector}' sector.

        **Target Audience:** Junior Data Analyst (Portfolio Project).

        **Step 1: Context Selection**
        Use this Client Profile: {selected_context}
        *Crucial:* The Client Profile describes the *situation* (e.g., Startup, Crisis). The Company's *actual industry* must be '{sector}'.
        (e.g., If sector is 'Fintech' and profile is 'Rapidly Scaling', the company is a Fintech Startup, NOT a generic SaaS).

        **Step 2: Task Selection**
        Below is a list of *Suggested Data Tasks* for inspiration.
        Select ONE Data Task that is highly relevant to a '{sector}' company.
        *Crucial:*
        - You may choose one from the list below if it fits well.
        - OR, **you may invent a completely different Data Task** if none of the suggestions fit the specific nuances of the '{sector}' sector perfectly.
        - Do not force an irrelevant task (e.g., don't pick 'Inventory' for a pure software company).

        [Suggested Archetypes]
        {archetypes_str}

        **Goal:** Write a compelling backstory for this specific client and their problem based on your selection.

        **Entropy Injection:**
        Random Seed: {random_seed}
        {avoid_str}

        **Guidelines:**
        1. **Relevance:** Ensure the selected task is logical for the sector.
        2. **Scope:** Focus on descriptive and diagnostic analysis (Trends, KPIs, Comparisons, Aggregations). Avoid complex predictive modeling, supply chain planning, or operations research tasks that are outside the scope of a Junior Data Analyst.
        3. **Creativity:** Make it interesting, but keep it grounded in reality. Avoid sci-fi or overly magical elements unless the sector strictly demands it.
        4. **Company:** Invent a unique, memorable name. Do NOT use generic names like "Company A".
        5. **Context:** Provide rich business details. *Why* is this specific analysis crucial right now?

        Output ONLY valid JSON:
        {{
            "title": "Creative Project Title",
            "company_name": "Name",
            "business_problem": "Short description of the core problem",
            "description": "Detailed 3-4 sentence backstory."
        }}
        """
        return llm_service.generate_json(prompt, api_key, temperature=0.95)

    def _generate_data_recipe(self, narrative: dict, api_key: str):
        prompt = f"""
        Act as a Senior Data Architect.
        You have been given the following project scenario:

        **Title:** {narrative.get('title')}
        **Company:** {narrative.get('company_name')}
        **Problem:** {narrative.get('business_problem')}
        **Description:** {narrative.get('description')}

        **Task:** Design a synthetic dataset schema (recipe) that perfectly matches this scenario.

        **Requirements:**
        1. **Anchor Entity:** Pick the most relevant main entity (e.g., 'Product', 'User', 'Transaction', 'Ad Campaign').
           - Provide 5-10 REALISTIC, specific options for this entity (e.g., "Sony WH-1000XM5" not "Headphones").
        2. **Correlated Columns:** Create columns that have logical relationships with the Anchor.
        3. **Tasks:** Define 3-5 analysis questions solvable with this data (Focus on SQL/Pandas aggregation and visualization).

        Output a JSON merging the scenario and the recipe:
        {{
            "title": "{narrative.get('title')}",
            "description": "{narrative.get('description')}",
            "tasks": ["List of 3-5 analysis tasks"],
            "recipe": {{
                "anchor_entity": {{
                    "name": "Name of entity",
                    "options": ["List", "of", "REAL", "examples"],
                    "weights": [0.1, 0.2, "etc (sum to 1)"]
                }},
                "correlated_columns": [
                    {{
                        "name": "column_name_snake_case",
                        "type": "numeric/boolean",
                        "description": "Desc",
                        "rules": {{ "Option1": {{"min":0, "max":10}} }}
                    }}
                ],
                "faker_columns": [
                    {{"name": "col_name", "faker_method": "name/date_this_year/city/email"}}
                ]
            }},
            "display_schema": [
                {{"name": "col_name", "type": "Type", "description": "Short explanation (less than a sentence)."}}
            ]
        }}
        """
        return llm_service.generate_json(prompt, api_key, temperature=0.8)

    def refine_data_recipe(self, narrative: dict, feedback: list, api_key: str):
        """
        Refines the data recipe based on verification feedback while strictly adhering to the original narrative.
        """
        feedback_str = "\n".join([f"- {item}" for item in feedback])

        prompt = f"""
        Act as a Senior Data Architect.

        **CRITICAL FIX REQUIRED:**
        A previous attempt to generate a dataset for this scenario FAILED verification.
        You must generate a **CORRECTED** recipe that resolves the following issues:

        {feedback_str}

        **Constraint:**
        - You MUST keep the same Scenario (Title, Company, Problem).
        - You MUST fix the specific schema/type mismatches mentioned above.
        - Ensure the 'display_schema' types match the 'recipe' generation logic (e.g., if you say 'String', do not generate booleans).

        **Project Scenario (DO NOT CHANGE):**
        **Title:** {narrative.get('title')}
        **Company:** {narrative.get('company_name')}
        **Problem:** {narrative.get('business_problem')}
        **Description:** {narrative.get('description')}

        **Task:** Design a corrected synthetic dataset schema (recipe).

        **Requirements:**
        1. **Anchor Entity:** Pick the most relevant main entity (e.g., 'Product', 'User', 'Transaction', 'Ad Campaign').
           - Provide 5-10 REALISTIC, specific options for this entity (e.g., "Sony WH-1000XM5" not "Headphones").
        2. **Correlated Columns:** Create columns that have logical relationships with the Anchor.
        3. **Tasks:** Define 3-5 analysis questions solvable with this data.

        Output a JSON merging the scenario and the recipe:
        {{
            "title": "{narrative.get('title')}",
            "description": "{narrative.get('description')}",
            "tasks": ["List of 3-5 analysis tasks"],
            "recipe": {{
                "anchor_entity": {{
                    "name": "Name of entity",
                    "options": ["List", "of", "REAL", "examples"],
                    "weights": [0.1, 0.2, "etc (sum to 1)"]
                }},
                "correlated_columns": [
                    {{
                        "name": "column_name_snake_case",
                        "type": "numeric/boolean",
                        "description": "Desc",
                        "rules": {{ "Option1": {{"min":0, "max":10}} }}
                    }}
                ],
                "faker_columns": [
                    {{"name": "col_name", "faker_method": "name/date_this_year/city/email"}}
                ]
            }},
            "display_schema": [
                {{"name": "col_name", "type": "Type", "description": "Short explanation (less than a sentence)."}}
            ]
        }}
        """
        return llm_service.generate_json(prompt, api_key, temperature=0.5) # Lower temp for strict adherence

    # Legacy wrapper for compatibility if needed, but we will update app.py
    def generate_project_definition(self, sector: str, api_key: str = None, previous_context: list = None):
        return self.orchestrate_project_generation(sector, api_key, previous_context)

    def _sanitize_column_name(self, name: str) -> str:
        # Lowercase
        name = name.lower()
        # Replace spaces with underscores
        name = name.replace(" ", "_")
        # Remove non-alphanumeric (except underscore)
        name = re.sub(r'[^a-z0-9_]', '', name)
        # Ensure it doesn't start with a number
        if name and name[0].isdigit():
            name = "_" + name
        return name

    def generate_dataset(self, recipe: dict, rows: int = 10000) -> pd.DataFrame:
        data = {}

        # 1. Generate Anchor Column
        anchor = recipe['anchor_entity']
        anchor_name = self._sanitize_column_name(anchor['name'])
        options = anchor['options']
        weights = anchor['weights']

        # Normalize weights if needed
        try:
            weights = [float(w) for w in weights]
            total_weight = sum(weights)
            if abs(total_weight - 1.0) > 0.01:
                weights = [w / total_weight for w in weights]
        except:
            # Fallback to equal weights if parsing fails
            weights = [1.0/len(options)] * len(options)

        data[anchor_name] = np.random.choice(options, size=rows, p=weights)

        # 2. Generate Correlated Columns
        for col in recipe.get('correlated_columns', []):
            col_name = self._sanitize_column_name(col['name'])
            col_type = col['type']
            col_type_clean = col_type.lower()
            rules = col['rules']

            values = []
            for i in range(rows):
                anchor_val = data[anchor_name][i]
                rule = rules.get(anchor_val, rules.get('default'))

                # --- Helper logic to generate value based on type string ---
                def get_val_by_type(t_str, r=None):
                    # Numeric
                    if any(x in t_str for x in ['int', 'numeric', 'float', 'money', 'currency']):
                         if r and isinstance(r, dict):
                             min_v = r.get('min', 0)
                             max_v = r.get('max', 100)
                             if 'float' in t_str or isinstance(min_v, float) or isinstance(max_v, float):
                                 return np.random.uniform(min_v, max_v)
                             else:
                                 return np.random.randint(min_v, max_v + 1)
                         else:
                             if 'float' in t_str: return np.random.uniform(0, 100)
                             return np.random.randint(0, 100)

                    # Boolean
                    elif 'bool' in t_str:
                        prob = 0.5
                        if r is not None and isinstance(r, (int, float)):
                            prob = r
                        return np.random.random() < prob

                    # Date
                    elif any(x in t_str for x in ['date', 'time']):
                        return fake.date_this_year()

                    # String/Categorical/Default
                    else:
                        if r and isinstance(r, str):
                            return r
                        return fake.word()

                if rule is None:
                     val = get_val_by_type(col_type_clean)
                else:
                     val = get_val_by_type(col_type_clean, rule)

                values.append(val)

            data[col_name] = values

        # 3. Apply Fluff (Faker Columns)
        for col in recipe.get('faker_columns', []):
            col_name = self._sanitize_column_name(col['name'])
            method = col['faker_method']

            if hasattr(fake, method):
                data[col_name] = [getattr(fake, method)() for _ in range(rows)]
            else:
                # Fallback: Try to find a relevant Faker method based on keywords
                method_lower = method.lower()
                fallback_method = None

                if 'country' in method_lower: fallback_method = 'country'
                elif 'city' in method_lower: fallback_method = 'city'
                elif 'name' in method_lower: fallback_method = 'name'
                elif 'email' in method_lower: fallback_method = 'email'
                elif 'date' in method_lower: fallback_method = 'date_this_year'
                elif 'job' in method_lower: fallback_method = 'job'
                elif 'company' in method_lower: fallback_method = 'company'
                elif 'address' in method_lower: fallback_method = 'address'

                if fallback_method and hasattr(fake, fallback_method):
                    data[col_name] = [getattr(fake, fallback_method)() for _ in range(rows)]
                else:
                    data[col_name] = [fake.word() for _ in range(rows)]

        df = pd.DataFrame(data)

        # 4. Inject Chaos
        col_types = {anchor_name: 'categorical'}
        for col in recipe.get('correlated_columns', []):
            clean_name = self._sanitize_column_name(col['name'])
            col_types[clean_name] = col['type']
        for col in recipe.get('faker_columns', []):
            clean_name = self._sanitize_column_name(col['name'])
            method = col['faker_method']
            if 'date' in method:
                col_types[clean_name] = 'date'
            elif 'year' in method:
                col_types[clean_name] = 'numeric'
            else:
                col_types[clean_name] = 'string'

        df = chaos.apply_chaos(df, col_types)

        return df

project_generator = ProjectGenerator()
