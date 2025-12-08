import pandas as pd
import numpy as np
import random

class ChaosToolkit:
    """
    Introduces realistic data quality issues into a clean dataframe.
    """

    def inject_rogue_strings(self, df: pd.DataFrame, col_name: str, ratio: float = 0.05):
        """
        Forces a numeric column to object type by inserting rogue values like 'TBD', 'Error', '$'.
        """
        if col_name not in df.columns:
            return df

        # Ensure column is object type to accept strings
        df[col_name] = df[col_name].astype(object)

        rogue_values = ["TBD", "Error", "null", "N/A", "???", "$$$"]
        n_rows = len(df)
        n_rogue = int(n_rows * ratio)

        if n_rogue > 0:
            indices = np.random.choice(df.index, n_rogue, replace=False)
            df.loc[indices, col_name] = np.random.choice(rogue_values, n_rogue)

        return df

    def inject_date_confusion(self, df: pd.DataFrame, col_name: str, ratio: float = 0.1):
        """
        Mixes date formats in a date column (e.g. YYYY-MM-DD vs DD/MM/YYYY).
        """
        if col_name not in df.columns:
            return df

        # Ensure it's treated as object/string for mixed formatting
        df[col_name] = df[col_name].astype(object)

        n_rows = len(df)
        n_confused = int(n_rows * ratio)

        if n_confused > 0:
            indices = np.random.choice(df.index, n_confused, replace=False)

            # Assuming values are already date objects or strings.
            # If they are date objects, we format them.
            # If they are strings, we might need to parse first, but let's assume valid generation first.

            def confuse_date(val):
                if pd.isna(val): return val
                try:
                    # If it's a timestamp/date
                    if hasattr(val, 'strftime'):
                        # Return US format or swapped day/month randomly
                        formats = ['%d/%m/%Y', '%m-%d-%Y', '%Y.%m.%d']
                        return val.strftime(random.choice(formats))
                    # If it's a string, leave it (or try to parse? simpler to assume date obj input)
                    return val
                except:
                    return val

            # Apply confusion
            # We can't vectorise easily with random choice per row without apply,
            # or we split indices by format.
            # Simple apply for the selected indices:
            df.loc[indices, col_name] = df.loc[indices, col_name].apply(confuse_date)

        return df

    def apply_chaos(self, df: pd.DataFrame, recipe_columns: dict) -> pd.DataFrame:
        """
        Randomly selects attacks to run on the dataframe based on available column types.
        recipe_columns: dict of col_name -> type ('numeric', 'date', etc.)
        """
        # Identify candidates
        numeric_cols = [c for c, t in recipe_columns.items() if t in ['numeric', 'integer', 'float']]
        date_cols = [c for c, t in recipe_columns.items() if t in ['date', 'datetime']]

        attacks = []

        # 1. Random numeric corruption
        if numeric_cols and random.random() < 0.7: # 70% chance
            target = random.choice(numeric_cols)
            attacks.append(lambda d: self.inject_rogue_strings(d, target, ratio=0.03))

        # 2. Date format confusion
        if date_cols and random.random() < 0.6:
            target = random.choice(date_cols)
            attacks.append(lambda d: self.inject_date_confusion(d, target, ratio=0.05))

        # 3. Random Nulls (Classic)
        # We can still add general nulls
        if random.random() < 0.8:
            def inject_nulls(d):
                cols = list(d.columns)
                target = random.choice(cols)
                n_rows = len(d)
                n_nulls = int(n_rows * 0.05)
                indices = np.random.choice(d.index, n_nulls, replace=False)
                d.loc[indices, target] = np.nan
                return d
            attacks.append(inject_nulls)

        # Apply selected attacks
        for attack in attacks:
            df = attack(df)

        return df
