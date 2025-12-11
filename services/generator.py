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
    def generate_project_definition(self, sector: str, api_key: str = None):
        # Inject a random seed to force the LLM to diverge from its deterministic path
        random_seed = random.randint(1, 100000)

        prompt = f"""
        Act as an expert Data Science Mentor and Creative Writer.
        Generate a comprehensive and realistic data analysis project scenario for a Junior Data Analyst in the '{sector}' sector.

        **Entropy Injection:**
        Random Seed: {random_seed}
        (Use this seed to wildly vary the Company Name, Business Situation, and specific Data Problems. Do not repeat previous outputs.)

        **Creativity Guidelines:**
        1. **Company & Context:** Invent a unique, realistic company name and a specific, detailed business situation.
           - Do NOT use generic names like "Company A".
           - VARY the company stage (Startup vs Enterprise vs Non-profit).
           - VARY the core problem (e.g., Fraud, Efficiency, Growth, Retention, Logistics).
        2. **Diversity:** Ensure the scenario is NOT just a standard "Sales Analysis". Dig deep into sector-specific nuances (e.g., for 'AdTech', look at attribution models or bid density; for 'Healthcare', look at patient readmission or bed occupancy).
        3. **Data Realism:** For the `anchor_entity`, use REAL-WORLD examples specific to the sector.
           - Bad: "Option A", "Option B"
           - Good (Automotive): "Tesla Model 3", "Ford F-150", "Toyota Camry"
           - Good (Retail): "Wireless Headphones", "Running Shoes", "Smart Watch"
        4. **Correlations:** Ensure the rules for correlated columns reflect logical real-world relationships.

        Output a JSON with the following structure:
        {{
            "title": "Creative Project Title",
            "description": "Detailed 3-4 sentence scenario description describing the unique business context, the specific company, and the urgent problem to solve.",
            "tasks": ["List of 3-5 specific, actionable questions for the analyst (e.g., 'Calculate the impact of X on Y')"],
            "recipe": {{
                "anchor_entity": {{
                    "name": "Name of the main entity (e.g. 'car_model', 'department', 'subscription_tier')",
                    "options": ["List", "of", "5-10", "specific", "REAL-WORLD", "examples"],
                    "weights": [0.1, 0.2, "etc (must sum to 1, length match options)"]
                }},
                "correlated_columns": [
                    {{
                        "name": "column_name_snake_case",
                        "type": "numeric",
                        "description": "Description of the metric",
                        "rules": {{
                            "SpecificAnchorOption1": {{"min": 10, "max": 20}},
                            "SpecificAnchorOption2": {{"min": 50, "max": 100}},
                            "default": {{"min": 0, "max": 50}}
                        }}
                    }},
                    {{
                        "name": "another_column_snake_case",
                        "type": "boolean",
                        "description": "Description",
                        "rules": {{
                            "SpecificAnchorOption1": 0.8, // Probability of True
                            "SpecificAnchorOption2": 0.2
                        }}
                    }}
                ],
                "faker_columns": [
                    {{"name": "customer_name", "faker_method": "name"}},
                    {{"name": "date", "faker_method": "date_this_year"}},
                    {{"name": "email", "faker_method": "email"}},
                    {{"name": "city", "faker_method": "city"}}
                ]
            }},
            "display_schema": [
                {{"name": "column_name", "type": "Type", "description": "Short desc"}}
            ]
        }}
        """
        return llm_service.generate_json(prompt, api_key)

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
