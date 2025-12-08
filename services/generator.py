import pandas as pd
import numpy as np
from faker import Faker
import random
from .llm import llm_service

fake = Faker()

class ProjectGenerator:
    def generate_project_definition(self, sector: str):
        prompt = f"""
        Generate a data analysis project scenario for a Junior Data Analyst in the '{sector}' sector.

        Output a JSON with the following structure:
        {{
            "title": "Project Title",
            "description": "Detailed scenario description describing the business context and the problem to solve.",
            "tasks": ["List of 3-5 specific questions or tasks for the analyst"],
            "schema": [
                {{
                    "name": "column_name",
                    "type": "string|date|numeric|categorical|boolean",
                    "description": "Description of the column",
                    "distribution_hint": "Hint for data generation (e.g., 'uuid', 'name', 'date_this_year', 'normal(mean, std)', 'uniform(min, max)', 'categorical_options', 'company', 'address')"
                }}
            ],
            "insights": ["List of 2-3 hidden insights or patterns that should be present in the data"],
            "data_issues": ["List of 2-3 data quality issues to introduce (e.g., 'nulls in column X', 'duplicates', 'outliers')"]
        }}
        """
        return llm_service.generate_json(prompt)

    def generate_dataset(self, schema: list, rows: int = 1000) -> pd.DataFrame:
        data = {}

        for col in schema:
            name = col['name']
            col_type = col['type']
            hint = col.get('distribution_hint', '')

            if col_type == 'string':
                if 'uuid' in hint:
                    data[name] = [fake.uuid4() for _ in range(rows)]
                elif 'name' in hint:
                    data[name] = [fake.name() for _ in range(rows)]
                elif 'company' in hint:
                    data[name] = [fake.company() for _ in range(rows)]
                elif 'address' in hint:
                    data[name] = [fake.address() for _ in range(rows)]
                elif 'email' in hint:
                    data[name] = [fake.email() for _ in range(rows)]
                else:
                    data[name] = [fake.word() for _ in range(rows)]

            elif col_type == 'date':
                data[name] = [fake.date_between(start_date='-1y', end_date='today') for _ in range(rows)]

            elif col_type == 'numeric':
                if 'normal' in hint:
                    # Parse mean and std if possible, else default
                    try:
                        params = hint.replace('normal', '').strip('()').split(',')
                        mean = float(params[0]) if len(params) > 0 else 100
                        std = float(params[1]) if len(params) > 1 else 10
                        data[name] = np.random.normal(mean, std, rows)
                    except:
                        data[name] = np.random.normal(100, 20, rows)
                elif 'uniform' in hint:
                    try:
                        params = hint.replace('uniform', '').strip('()').split(',')
                        min_val = float(params[0]) if len(params) > 0 else 0
                        max_val = float(params[1]) if len(params) > 1 else 1000
                        data[name] = np.random.uniform(min_val, max_val, rows)
                    except:
                        data[name] = np.random.uniform(0, 100, rows)
                else:
                    data[name] = np.random.randint(0, 1000, rows)

            elif col_type == 'categorical':
                # Try to extract options if provided in hint as list
                if '[' in hint and ']' in hint:
                    try:
                        # Safer eval for list parsing
                        options = eval(hint[hint.find('['):hint.find(']')+1])
                        data[name] = np.random.choice(options, rows)
                    except:
                         data[name] = [fake.word() for _ in range(rows)]
                else:
                    data[name] = [fake.color_name() for _ in range(rows)] # Fallback

            elif col_type == 'boolean':
                data[name] = np.random.choice([True, False], rows)

            else:
                 data[name] = [fake.word() for _ in range(rows)]

        df = pd.DataFrame(data)

        # Introduce some basic messiness
        # Random nulls
        for col in df.columns:
            if random.random() < 0.3: # 30% chance a column has nulls
                df.loc[df.sample(frac=0.05).index, col] = np.nan

        return df

project_generator = ProjectGenerator()
