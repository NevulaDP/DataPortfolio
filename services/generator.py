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
            "description": "Two concise paragraphs (approx. 2-3 sentences each). Use \\n\\n to separate them. Do not exceed 80 words total.",
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

        **Task:** Define a "Schema Table" for a synthetic dataset that perfectly matches this scenario.

        **Requirements:**
        1. **Anchor Entity:** Pick the most relevant main entity (e.g., 'Product', 'User', 'Transaction', 'Ad Campaign').
           - Provide 5-10 REALISTIC, specific options for this entity (e.g., "Sony WH-1000XM5" not "Headphones").
        2. **Schema Definition:** Define every single column in the dataset with a strict type.
           - Types Allowed: 'categorical', 'date', 'numeric', 'id', 'text'.
           - **CRITICAL RULE:** For 'categorical' columns, you **MUST** provide a list of valid options.
           - **CRITICAL RULE:** Use 'categorical' for ANY column with a finite set of values (Status, Region, Department, Priority, etc.).
           - **CRITICAL RULE:** For 'numeric' columns, use ONLY 'min' and 'max'. Do **NOT** provide 'options' or 'faker_method'.
           - Use 'id' only for high-cardinality unique identifiers (UUIDs).
           - Use 'text' only for names, emails, addresses, or free text notes.
        3. **Relationships:** Ensure date logic is consistent (e.g., shipped after ordered).

        **Constraint on Calculated Columns:**
        - **Do NOT** include calculated/derived columns (e.g., "profit", "days_to_ship") in the dataset. Provide raw data instead.

        Output ONLY valid JSON in this specific "Schema-First" format:
        {{
            "title": "{narrative.get('title')}",
            "description": "{narrative.get('description')}",
            "tasks": ["List of 3-5 analysis tasks"],
            "schema_list": [
                {{
                    "name": "transaction_id",
                    "type": "id",
                    "faker_method": "uuid4",
                    "description": "Unique ID for transaction"
                }},
                {{
                    "name": "customer_name",
                    "type": "text",
                    "faker_method": "name",
                    "description": "Name of customer"
                }},
                {{
                    "name": "product_name",
                    "type": "anchor",
                    "options": ["Sony WH-1000XM5", "Bose QC45", "Apple AirPods Max"],
                    "description": "The main product sold"
                }},
                {{
                    "name": "region",
                    "type": "categorical",
                    "options": ["North America", "Europe", "Asia"],
                    "weights": [0.5, 0.3, 0.2],
                    "description": "Sales region"
                }},
                {{
                    "name": "purchase_date",
                    "type": "date",
                    "range_start": "2023-01-01",
                    "range_end": "2023-12-31",
                    "description": "Date of purchase"
                }},
                {{
                    "name": "shipping_date",
                    "type": "date",
                    "depends_on": "purchase_date",
                    "offset_days_min": 1,
                    "offset_days_max": 7,
                    "description": "Date of shipping"
                }},
                {{
                    "name": "price",
                    "type": "numeric",
                    "min": 10,
                    "max": 500,
                    "description": "Unit price"
                }}
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

    def _generate_dataset_legacy(self, recipe: dict, rows: int = 10000) -> pd.DataFrame:
        """Legacy generation logic for backward compatibility."""
        data = {}

        # 1. Generate Anchor Column
        anchor = recipe.get('anchor_entity', {})
        anchor_name = self._sanitize_column_name(anchor.get('name', 'entity'))
        options = anchor.get('options', ['Item A', 'Item B'])
        weights = anchor.get('weights', [1.0/len(options)]*len(options))

        # Normalize weights
        try:
            weights = [float(w) for w in weights]
            total_weight = sum(weights)
            if abs(total_weight - 1.0) > 0.01:
                weights = [w / total_weight for w in weights]
        except:
            weights = [1.0/len(options)] * len(options)

        data[anchor_name] = np.random.choice(options, size=rows, p=weights)

        # 2. Categorical
        for col in recipe.get('categorical_columns', []):
            col_name = self._sanitize_column_name(col['name'])
            opts = col['options']
            wts = col.get('weights', None)
            if wts:
                try:
                    wts = [float(w) for w in wts]
                    total = sum(wts)
                    if abs(total - 1.0) > 0.01: wts = [w / total for w in wts]
                except: wts = None
            data[col_name] = np.random.choice(opts, size=rows, p=wts)

        # 3. Dates
        processed_dates = set()
        pending_dates = [d for d in recipe.get('date_columns', [])]
        loop_counter = 0
        max_loops = len(pending_dates) * 2

        while pending_dates and loop_counter < max_loops:
            loop_counter += 1
            col = pending_dates.pop(0)
            col_name = self._sanitize_column_name(col['name'])
            dtype = col.get('type', 'base')

            if dtype == 'base':
                start_str = col.get('range_start', '2023-01-01')
                end_str = col.get('range_end', '2023-12-31')
                try:
                    start_date = datetime.strptime(start_str, "%Y-%m-%d")
                    end_date = datetime.strptime(end_str, "%Y-%m-%d")
                    delta = (end_date - start_date).days
                    random_days = np.random.randint(0, delta + 1, size=rows)
                    base = pd.to_datetime(start_date)
                    data[col_name] = (base + pd.to_timedelta(random_days, unit='D')).date
                    processed_dates.add(col_name)
                except:
                    data[col_name] = [fake.date_this_year() for _ in range(rows)]
                    processed_dates.add(col_name)

            elif dtype == 'dependent':
                dependency = self._sanitize_column_name(col.get('depends_on', ''))
                if dependency in data:
                    min_off = col.get('offset_days_min', 0)
                    max_off = col.get('offset_days_max', 30)
                    offsets = np.random.randint(min_off, max_off + 1, size=rows)
                    base_series = pd.to_datetime(pd.Series(data[dependency]))
                    data[col_name] = (base_series + pd.to_timedelta(offsets, unit='D')).dt.date
                    processed_dates.add(col_name)
                else:
                    pending_dates.append(col)

        # 4. Numeric
        for col in recipe.get('numeric_columns', []):
            col_name = self._sanitize_column_name(col['name'])
            data[col_name] = np.random.randint(0, 100, size=rows) # Simplified legacy fallback

        # 5. Faker (With Safety Net)
        for col in recipe.get('faker_columns', []):
            col_name = self._sanitize_column_name(col['name'])
            method = col.get('faker_method', 'word')

            # Interception Logic
            is_generic_method = method.lower() in ['word', 'words', 'sentence', 'text', 'lorem', 'string']
            categorical_keywords = ['status', 'type', 'category', 'class', 'tier', 'mode', 'segment', 'group', 'level', 'priority', 'region', 'department']
            name_implies_category = any(k in col_name.lower() for k in categorical_keywords)

            should_intercept = (is_generic_method and name_implies_category)

            if hasattr(fake, method) and not should_intercept:
                data[col_name] = [getattr(fake, method)() for _ in range(rows)]
            else:
                clean_title = col['name'].replace('_', ' ').title()
                placeholder_opts = [f"{clean_title} {char}" for char in ['A', 'B', 'C', 'D']]
                data[col_name] = np.random.choice(placeholder_opts, size=rows)

        df = pd.DataFrame(data)

        # Chaos Injection for Legacy
        col_types = {anchor_name: 'categorical'}
        for col in recipe.get('categorical_columns', []):
            col_types[self._sanitize_column_name(col['name'])] = 'categorical'
        for col in recipe.get('date_columns', []):
            col_types[self._sanitize_column_name(col['name'])] = 'date'
        for col in recipe.get('numeric_columns', []):
            col_types[self._sanitize_column_name(col['name'])] = 'numeric'
        for col in recipe.get('faker_columns', []):
            col_types[self._sanitize_column_name(col['name'])] = 'string'

        return chaos.apply_chaos(df, col_types)

    def generate_dataset(self, recipe: dict, rows: int = 10000, apply_simulation_chaos: bool = True) -> pd.DataFrame:
        data = {}

        # New "Schema-First" Architecture
        # We process the 'schema_list' which contains ALL column definitions (replacing the old split lists)

        schema = recipe.get('schema_list', [])

        # Support for legacy/old format during migration or if prompt fails
        if not schema:
            # Fallback to old generation logic if 'schema_list' is missing
            return self._generate_dataset_legacy(recipe, rows)

        # 1. Process Anchor / Independent Columns First
        # We need to find the anchor first to handle dependencies if any
        # But in the new schema, dependencies are simpler (dates depend on dates).

        # Two-pass approach:
        # Pass 1: Generate Independent (Categorical, ID, Text, Base Dates, Anchor)
        # Pass 2: Generate Dependent (Dependent Dates, Numeric/Correlated)

        pending_cols = []

        for col in schema:
            col_name = self._sanitize_column_name(col['name'])
            col_type = col.get('type', 'text').lower()

            # PRIORITY CHECK: If options are explicitly provided, force categorical behavior
            # This handles cases where LLM says type="text" or "string" but provides options.
            # EXCEPTION: If strictly defined as 'numeric', we ignore options to prevent string contamination.
            if col.get('options') and len(col['options']) > 0 and col_type != 'numeric':
                col_type = 'categorical'

            # --- Categorical & Anchor ---
            if col_type in ['categorical', 'anchor']:
                options = col.get('options', [])
                if not options:
                    # Safety Net: No options provided for categorical?
                    clean_title = col_name.replace('_', ' ').title()
                    options = [f"{clean_title} A", f"{clean_title} B", f"{clean_title} C"]

                weights = col.get('weights', None)
                if weights:
                    try:
                        weights = [float(w) for w in weights]
                        # Normalize
                        total = sum(weights)
                        if abs(total - 1.0) > 0.01:
                            weights = [w / total for w in weights]
                    except:
                        weights = None

                # If weights length mismatch, ignore weights
                if weights and len(weights) != len(options):
                    weights = None

                data[col_name] = np.random.choice(options, size=rows, p=weights)

            # --- ID / Text (Faker) ---
            elif col_type in ['id', 'text']:
                method = col.get('faker_method', 'word')

                # Interception Logic (Still good to have!)
                is_generic_method = method.lower() in ['word', 'words', 'sentence', 'text', 'lorem', 'string']
                categorical_keywords = ['status', 'type', 'category', 'class', 'tier', 'mode', 'segment', 'group', 'level', 'priority', 'region', 'department', 'platform', 'channel']
                name_implies_category = any(k in col_name.lower() for k in categorical_keywords)

                should_intercept = (is_generic_method and name_implies_category)

                if should_intercept:
                    # Force categorical generation
                    clean_title = col_name.replace('_', ' ').title()
                    placeholder_opts = [f"{clean_title} {char}" for char in ['A', 'B', 'C', 'D']]
                    data[col_name] = np.random.choice(placeholder_opts, size=rows)
                elif hasattr(fake, method):
                    data[col_name] = [getattr(fake, method)() for _ in range(rows)]
                else:
                    # Fallback Faker
                    if 'email' in col_name.lower(): data[col_name] = [fake.email() for _ in range(rows)]
                    elif 'name' in col_name.lower(): data[col_name] = [fake.name() for _ in range(rows)]
                    elif 'id' in col_name.lower(): data[col_name] = [str(uuid.uuid4()) for _ in range(rows)]
                    else: data[col_name] = [fake.word() for _ in range(rows)]

            # --- Numeric (Defer to pass 2 for correlation? Or simple range?) ---
            elif col_type == 'numeric':
                # Simple numeric for now, can add correlation later if needed
                # The prompt asks for min/max
                min_val = col.get('min', 0)
                max_val = col.get('max', 100)
                is_float = isinstance(min_val, float) or isinstance(max_val, float)

                if is_float:
                    data[col_name] = np.random.uniform(min_val, max_val, size=rows)
                else:
                    data[col_name] = np.random.randint(min_val, max_val + 1, size=rows)

            # --- Date (Base) ---
            elif col_type == 'date':
                if 'depends_on' in col:
                    pending_cols.append(col) # Handle in Pass 2
                else:
                    # Base Date
                    start_str = col.get('range_start', '2023-01-01')
                    end_str = col.get('range_end', '2023-12-31')
                    try:
                        start_date = datetime.strptime(start_str, "%Y-%m-%d")
                        end_date = datetime.strptime(end_str, "%Y-%m-%d")
                        delta = (end_date - start_date).days
                        random_days = np.random.randint(0, delta + 1, size=rows)
                        base = pd.to_datetime(start_date)
                        data[col_name] = (base + pd.to_timedelta(random_days, unit='D'))
                    except:
                        data[col_name] = [pd.to_datetime(fake.date_this_year()) for _ in range(rows)]

        # Pass 2: Dependent Columns
        for col in pending_cols:
            col_name = self._sanitize_column_name(col['name'])
            col_type = col.get('type', 'text').lower()

            if col_type == 'date' and 'depends_on' in col:
                dep_name = self._sanitize_column_name(col['depends_on'])
                if dep_name in data:
                    min_off = col.get('offset_days_min', 0)
                    max_off = col.get('offset_days_max', 30)
                    offsets = np.random.randint(min_off, max_off + 1, size=rows)
                    base_series = pd.to_datetime(pd.Series(data[dep_name]))
                    data[col_name] = (base_series + pd.to_timedelta(offsets, unit='D'))
                else:
                    # Fallback if dependency missing
                    data[col_name] = [pd.to_datetime(fake.date_this_year()) for _ in range(rows)]

        df = pd.DataFrame(data)

        # 6. Inject Chaos (Optional)
        if apply_simulation_chaos:
            df = self.apply_chaos_to_data(df, recipe)

        return df

    def apply_chaos_to_data(self, df: pd.DataFrame, recipe: dict) -> pd.DataFrame:
        """
        Applies chaos simulation to an existing dataframe based on the recipe schema.
        Useful for applying chaos AFTER verification.
        """
        col_types = {}
        schema = recipe.get('schema_list', [])

        # New Schema Logic
        if schema:
            for col in schema:
                clean_name = self._sanitize_column_name(col['name'])
                c_type = col.get('type', 'text')
                if c_type == 'anchor': col_types[clean_name] = 'categorical'
                elif c_type == 'id': col_types[clean_name] = 'string'
                else: col_types[clean_name] = c_type
        else:
            # Legacy Logic (Simplified reconstruction if needed)
            pass

        return chaos.apply_chaos(df, col_types)

project_generator = ProjectGenerator()
