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
            # Retail/General Business
            "Sales Trend Analysis (identifying seasonal patterns and top performers)",
            "Customer Segmentation & Profiling (grouping users by behavior)",
            "Product Performance Review (analyzing sales vs returns)",
            "Customer Churn Analysis (identifying at-risk customers)",
            "Pricing & Discount Analysis (impact of discounts on revenue)",
            "Marketing Campaign Performance (ROI and conversion rates)",
            "Inventory Turnover & Stock Analysis (identifying slow-moving items)",
            "Operational KPI Dashboarding (tracking core business metrics)",

            # AdTech / High Tech / SaaS
            "Ad Campaign Performance & Attribution (CTR, CPC, Conversion analysis)",
            "Feature Usage & Adoption Analysis (SaaS product metrics)",
            "A/B Test Result Analysis (comparing control vs variant groups)",
            "User Engagement & Session Analysis (time on site, bounce rates)",

            # General
            "Anomaly Detection (investigating data irregularities)"
        ]

        # 2. Business Contexts (Scale/Stage)
        contexts = [
            "A rapidly scaling tech startup running out of runway",
            "A stable, family-owned business trying to modernize",
            "A large legacy corporation facing a PR crisis",
            "A non-profit organization struggling with donor retention",
            "A high-volume e-commerce giant facing stiff competition",
            "A boutique luxury brand expanding to mass market",
            "A B2B SaaS platform focused on user retention",
            "A digital media agency optimizing ad spend for clients"
        ]

        # Select one of each
        selected_archetype = random.choice(archetypes)
        selected_context = random.choice(contexts)

        avoid_str = ""
        if previous_context:
            avoid_str = "\n**FORBIDDEN TERMS (DO NOT USE):**\n" + ", ".join(previous_context) + "\n(You MUST generate a completely different company and scenario from these.)"

        prompt = f"""
        Act as an expert Creative Writer and Data Science Mentor.
        Create a unique, detailed, and realistic scenario for a Data Analysis project in the '{sector}' sector.

        **Target Audience:** Junior Data Analyst (Portfolio Project).

        **Structural Constraints:**
        1. **Client Profile:** {selected_context}.
        2. **Core Data Task:** {selected_archetype}.

        **Goal:** Write a compelling backstory for this specific client and their problem.

        **Entropy Injection:**
        Random Seed: {random_seed}
        {avoid_str}

        **Guidelines:**
        1. **Scope:** Focus on descriptive and diagnostic analysis (Trends, KPIs, Comparisons, Aggregations). Avoid complex predictive modeling, supply chain planning, or operations research tasks that are outside the scope of a Junior Data Analyst.
        2. **Creativity:** Make it interesting, but keep it grounded in reality. Avoid sci-fi or overly magical elements unless the sector strictly demands it.
        3. **Company:** Invent a unique, memorable name. Do NOT use generic names like "Company A".
        4. **Context:** Provide rich business details. *Why* is this specific analysis crucial right now?

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
            rules = col['rules']

            values = []
            for i in range(rows):
                anchor_val = data[anchor_name][i]
                rule = rules.get(anchor_val, rules.get('default'))

                if rule is None:
                    if col_type == 'numeric':
                        val = np.random.randint(0, 100)
                    else:
                        val = random.choice([True, False])
                else:
                    if col_type == 'numeric':
                        min_v = rule.get('min', 0)
                        max_v = rule.get('max', 100)
                        if isinstance(min_v, float) or isinstance(max_v, float):
                            val = np.random.uniform(min_v, max_v)
                        else:
                            val = np.random.randint(min_v, max_v + 1)
                    elif col_type == 'boolean':
                        prob = rule if isinstance(rule, (int, float)) else 0.5
                        val = np.random.random() < prob
                    else:
                        val = None
                values.append(val)

            data[col_name] = values

        # 3. Apply Fluff (Faker Columns)
        for col in recipe.get('faker_columns', []):
            col_name = self._sanitize_column_name(col['name'])
            method = col['faker_method']

            if hasattr(fake, method):
                data[col_name] = [getattr(fake, method)() for _ in range(rows)]
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
