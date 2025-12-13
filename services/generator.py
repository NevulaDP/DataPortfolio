import pandas as pd
import numpy as np
from faker import Faker
import random
import json
import re
from datetime import datetime, timedelta
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

        # Merge Granularity from Narrative to Recipe (Manual Injection)
        if "dataset_granularity" in narrative:
            full_project["dataset_granularity"] = narrative["dataset_granularity"]

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

        **Step 0: Define Granularity**
        Explicitly define what a single row in the dataset represents (e.g., "Each row represents a single customer transaction," "Each row represents a daily inventory snapshot," etc.). This is crucial for the data schema design.

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
            "description": "Detailed 3-4 sentence backstory.",
            "dataset_granularity": "Each row represents..."
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
        **Row Granularity:** {narrative.get('dataset_granularity', 'Not specified')}

        **Task:** Design a synthetic dataset schema (recipe) that perfectly matches this scenario.

        **Requirements:**
        1. **Anchor Entity:** Pick the most relevant main entity (e.g., 'Product', 'User', 'Transaction', 'Ad Campaign').
           - Provide 5-10 REALISTIC, specific options for this entity (e.g., "Sony WH-1000XM5" not "Headphones").
        2. **Categorical Columns (Priority):** Identify ALL columns that represent categories, statuses, types, priorities, labels, platforms, or regions.
           - **RULE:** If a column represents a concept with a finite set of possibilities (e.g., "Platform", "Region", "Tier", "Category", "Status", "Department", "Role", "Class"), it **MUST** be a `categorical_column` with a defined list of options.
           - **STRICT FORBIDDEN:** You must NOT use `faker_columns` for these types of fields.
           - Explicitly list the valid options for each categorical column.
        3. **Faker Columns (Restricted):** ONLY use `faker_columns` for these specific high-cardinality identity types: `name`, `email`, `address`, `phone_number`, `uuid4`, `date_this_year`, `company`, `job`, `city`, `country`.
           - **ANYTHING ELSE IS FORBIDDEN** in `faker_columns` and must be moved to `categorical_columns`.
        4. **Date Columns:** Define date columns. **Crucially**, if dates must follow a logic (e.g. 'shipped_at' must be after 'created_at'), define this dependency.
           - Use 'base' type for independent dates.
           - Use 'dependent' type for dates that follow another date, with an offset in days.
        4. **Correlated/Numeric Columns:** Columns that depend on the Anchor Entity (e.g. Price depends on Product).
        5. **Tasks:** Define 3-5 analysis questions.

        **Constraint on Calculated Columns:**
        - **Do NOT** include calculated/derived columns (e.g., "profit", "days_to_ship") in the dataset. Provide raw data instead.
        - Instead, provide the raw data (e.g., "signup_date", "revenue", "cost", "birthdate") and add a **Task** for the analyst to derive them.

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
                "categorical_columns": [
                    {{
                        "name": "status",
                        "options": ["Pending", "Shipped", "Delivered"],
                        "weights": [0.1, 0.3, 0.6]
                    }},
                    {{
                        "name": "department",
                        "options": ["Sales", "Engineering", "HR"],
                        "weights": [0.5, 0.3, 0.2]
                    }}
                ],
                "date_columns": [
                    {{
                        "name": "signup_date",
                        "type": "base",
                        "range_start": "2023-01-01",
                        "range_end": "2023-12-31"
                    }},
                    {{
                        "name": "last_login",
                        "type": "dependent",
                        "depends_on": "signup_date",
                        "offset_days_min": 1,
                        "offset_days_max": 30
                    }}
                ],
                "numeric_columns": [
                    {{
                        "name": "price",
                        "type": "numeric/integer",
                        "description": "Desc",
                        "rules": {{ "Option1": {{"min":0, "max":10}} }}
                    }}
                ],
                "faker_columns": [
                    {{"name": "customer_name", "faker_method": "name"}},
                    {{"name": "email", "faker_method": "email"}},
                    {{"name": "transaction_id", "faker_method": "uuid4"}}
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
        - Ensure 'date_columns' logic prevents date paradoxes.
        - **STRICT RULE:** Ensure 'categorical_columns' are used for ALL finite sets (Status, Type, Region, Department, Platform, Tier). **DO NOT** use `faker_columns` for these.
        - **STRICT RULE:** `faker_columns` are ONLY for: `name`, `email`, `address`, `phone_number`, `uuid4`, `date_this_year`, `company`, `job`, `city`, `country`.

        **Project Scenario (DO NOT CHANGE):**
        **Title:** {narrative.get('title')}
        **Company:** {narrative.get('company_name')}
        **Problem:** {narrative.get('business_problem')}
        **Description:** {narrative.get('description')}
        **Row Granularity:** {narrative.get('dataset_granularity', 'Not specified')}

        **Task:** Design a corrected synthetic dataset schema (recipe).

        Output a JSON merging the scenario and the recipe (same format as before):
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
                "categorical_columns": [
                    {{
                        "name": "status",
                        "options": ["Pending", "Shipped", "Delivered"],
                        "weights": [0.1, 0.3, 0.6]
                    }}
                ],
                "date_columns": [
                    {{
                        "name": "signup_date",
                        "type": "base",
                        "range_start": "2023-01-01",
                        "range_end": "2023-12-31"
                    }},
                    {{
                        "name": "last_login",
                        "type": "dependent",
                        "depends_on": "signup_date",
                        "offset_days_min": 1,
                        "offset_days_max": 30
                    }}
                ],
                "numeric_columns": [
                    {{
                        "name": "price",
                        "type": "numeric/integer",
                        "description": "Desc",
                        "rules": {{ "Option1": {{"min":0, "max":10}} }}
                    }}
                ],
                "faker_columns": [
                    {{"name": "col_name", "faker_method": "name/city/email"}}
                ]
            }},
            "display_schema": [
                {{"name": "col_name", "type": "Type", "description": "Short explanation (less than a sentence)."}}
            ]
        }}
        """
        return llm_service.generate_json(prompt, api_key, temperature=0.5)

    # Legacy wrapper for compatibility if needed
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

        # 2. Generate Categorical Columns (Independent)
        for col in recipe.get('categorical_columns', []):
            col_name = self._sanitize_column_name(col['name'])
            opts = col['options']
            wts = col.get('weights', [1.0/len(opts)]*len(opts))

            try:
                wts = [float(w) for w in wts]
                total = sum(wts)
                if abs(total - 1.0) > 0.01:
                    wts = [w / total for w in wts]
            except:
                wts = [1.0/len(opts)] * len(opts)

            data[col_name] = np.random.choice(opts, size=rows, p=wts)

        # 3. Generate Date Columns (Base + Dependent)
        date_cols = recipe.get('date_columns', [])

        # Sort: Base columns first, then dependent
        # A simple way is to process "base" first, then "dependent"
        # If there are chains (A->B->C), we might need a loop or topological sort.
        # Given the prompt instruction is simple (base vs dependent), 2 passes should suffice for now.
        # But a while loop is safer for chains.

        processed_dates = set()
        pending_dates = [d for d in date_cols]

        # Guard against infinite loops if dependencies are cyclic or missing
        loop_counter = 0
        max_loops = len(pending_dates) * 2

        while pending_dates and loop_counter < max_loops:
            loop_counter += 1
            col = pending_dates.pop(0)
            col_name = self._sanitize_column_name(col['name'])
            dtype = col.get('type', 'base')

            if dtype == 'base':
                # Generate random dates in range
                start_str = col.get('range_start', '2023-01-01')
                end_str = col.get('range_end', '2023-12-31')
                try:
                    start_date = datetime.strptime(start_str, "%Y-%m-%d")
                    end_date = datetime.strptime(end_str, "%Y-%m-%d")
                    delta = (end_date - start_date).days

                    random_days = np.random.randint(0, delta + 1, size=rows)
                    # Vectorized date addition
                    # We can't add int array to date object directly in standard python without pandas or numpy hacks
                    # Using pd.to_datetime makes this easier
                    base = pd.to_datetime(start_date)
                    date_series = base + pd.to_timedelta(random_days, unit='D')

                    if isinstance(date_series, pd.DatetimeIndex):
                         data[col_name] = date_series.date
                    else:
                         data[col_name] = date_series.dt.date

                except Exception as e:
                    # Fallback
                    data[col_name] = [fake.date_this_year() for _ in range(rows)]

                processed_dates.add(col_name)

            elif dtype == 'dependent':
                dependency = self._sanitize_column_name(col.get('depends_on', ''))
                if dependency in data:
                    # Generate based on dependency
                    min_off = col.get('offset_days_min', 0)
                    max_off = col.get('offset_days_max', 30)

                    offsets = np.random.randint(min_off, max_off + 1, size=rows)

                    # Convert dependency to datetime if not already (it should be date objects)
                    base_series = pd.to_datetime(data[dependency])
                    new_series = base_series + pd.to_timedelta(offsets, unit='D')
                    # If result is DatetimeIndex (happens if base_series is Index), it has no .dt accessor but has .date
                    if isinstance(new_series, pd.DatetimeIndex):
                        data[col_name] = new_series.date
                    else:
                        data[col_name] = new_series.dt.date

                    processed_dates.add(col_name)
                else:
                    # Dependency not ready yet, push back to queue
                    pending_dates.append(col)

        # If any pending left (circular or missing dependency), force generate as base
        for col in pending_dates:
             col_name = self._sanitize_column_name(col['name'])
             data[col_name] = [fake.date_this_year() for _ in range(rows)]


        # 4. Generate Numeric/Correlated Columns (Linked to Anchor)
        # Handle both old 'correlated_columns' and new 'numeric_columns' key for backward compat
        numeric_cols = recipe.get('numeric_columns', [])
        if not numeric_cols:
            numeric_cols = recipe.get('correlated_columns', [])

        for col in numeric_cols:
            col_name = self._sanitize_column_name(col['name'])
            col_type = col.get('type', 'numeric')
            col_type_clean = col_type.lower()
            rules = col.get('rules', {})

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

                    # Fallback
                    else:
                        # Fallback for unknown numeric types (often categorical strings put in numeric_columns by mistake)
                        clean_title = col_name.replace('_', ' ').title()
                        return f"{clean_title} {random.choice(['A', 'B', 'C', 'D', 'E'])}"

                if rule is None:
                     val = get_val_by_type(col_type_clean)
                else:
                     val = get_val_by_type(col_type_clean, rule)

                values.append(val)

            data[col_name] = values

        # 5. Apply Fluff (Faker Columns)
        for col in recipe.get('faker_columns', []):
            col_name = self._sanitize_column_name(col['name'])
            method = col['faker_method']

            # --- INTERCEPTION LOGIC FOR "LAZY LLM" ---
            # If the LLM uses a generic/nonsense method OR if the column name strongly implies a category,
            # we FORCE the safety net instead of using Faker.

            is_generic_method = method.lower() in ['word', 'words', 'sentence', 'text', 'lorem', 'string', 'random_element', 'random_letter']

            # Keywords that strongly suggest this should be a categorical column (finite set)
            categorical_keywords = ['status', 'type', 'category', 'class', 'tier', 'mode', 'segment', 'group', 'level', 'priority', 'region', 'department', 'platform', 'channel', 'source', 'medium', 'plan']
            name_implies_category = any(k in col_name.lower() for k in categorical_keywords)

            # If it's a generic method AND (it implies category OR it's just 'word'), we intercept.
            # We are aggressive here: if it's 'word'/'sentence', we almost always want structured data unless it's 'notes'/'description'.
            # If the column is 'description' or 'notes' or 'comment', we allow 'sentence'/'text'.
            is_free_text_field = any(k in col_name.lower() for k in ['note', 'comment', 'description', 'message', 'feedback', 'review'])

            should_intercept = (is_generic_method and not is_free_text_field) or (name_implies_category and is_generic_method)

            if hasattr(fake, method) and not should_intercept:
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
                    # SAFETY NET: If valid Faker method not found, assume it's a misclassified Categorical
                    # Generate a finite set of placeholder options based on column name
                    clean_title = col['name'].replace('_', ' ').title()
                    placeholder_opts = [f"{clean_title} {char}" for char in ['A', 'B', 'C', 'D', 'E']]
                    data[col_name] = np.random.choice(placeholder_opts, size=rows)

        df = pd.DataFrame(data)

        # 6. Inject Chaos
        # We need to construct a type map for the chaos tool
        col_types = {anchor_name: 'categorical'}

        for col in recipe.get('categorical_columns', []):
            clean_name = self._sanitize_column_name(col['name'])
            col_types[clean_name] = 'categorical'

        for col in recipe.get('date_columns', []):
            clean_name = self._sanitize_column_name(col['name'])
            col_types[clean_name] = 'date'

        for col in numeric_cols:
            clean_name = self._sanitize_column_name(col['name'])
            col_types[clean_name] = col.get('type', 'numeric')

        for col in recipe.get('faker_columns', []):
            clean_name = self._sanitize_column_name(col['name'])
            col_types[clean_name] = 'string' # Default for faker

        df = chaos.apply_chaos(df, col_types)

        return df

project_generator = ProjectGenerator()
