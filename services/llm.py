
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class LLMService:
    def __init__(self):
        # We don't store state on the instance anymore
        pass

    def _get_model(self, api_key: str):
        # Re-configuring globally is the only documented way for the high-level API.
        genai.configure(api_key=api_key)
        # Using Gemini 1.5 Pro as the "advanced" model (more capable than 1.5 Flash)
        return genai.GenerativeModel('gemini-1.5-pro')

    def list_available_models(self, api_key: str):
        try:
            genai.configure(api_key=api_key)
            return [m.name for m in genai.list_models()]
        except Exception as e:
            return [f"Error listing models: {str(e)}"]

    def generate_json(self, prompt: str, api_key: str = None) -> dict:
        key_to_use = api_key or os.getenv("GEMINI_API_KEY")
        if not key_to_use:
            return self._mock_response(prompt)

        try:
            model = self._get_model(key_to_use)
            # Force JSON response structure
            full_prompt = f"{prompt}\n\nRespond strictly with valid JSON."
            response = model.generate_content(full_prompt)
            # Simple cleaning of markdown code blocks if present
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            print(f"Error calling Gemini: {e}")
            if "404" in str(e) or "not found" in str(e).lower():
                models = self.list_available_models(key_to_use)
                return {"error": f"Model 'gemini-1.5-pro' not found. Your key has access to: {', '.join(models)}"}
            return self._mock_response(prompt)

    def generate_text(self, prompt: str, api_key: str = None) -> str:
        key_to_use = api_key or os.getenv("GEMINI_API_KEY")
        if not key_to_use:
            return "This is a mock response from the Senior Agent. Please set GEMINI_API_KEY to get real responses."

        try:
            model = self._get_model(key_to_use)
            # Add system instruction to prompt for Socratic guidance
            system_instruction = """
            You are a Senior Data Analyst mentor guiding a Junior Analyst.
            Do NOT provide direct code solutions or SQL queries immediately.
            Instead, guide the user on how to think about the problem.
            Ask leading questions, suggest concepts (e.g., 'Have you thought about grouping by...?'),
            and help them breakdown the task.
            Only provide code snippets if the user is stuck after multiple attempts or explicitly asks for syntax help.
            Be encouraging and constructive.
            """
            full_prompt = f"{system_instruction}\n\n{prompt}"

            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            print(f"Error calling Gemini: {e}")
            if "404" in str(e) or "not found" in str(e).lower():
                models = self.list_available_models(key_to_use)
                return f"Error: Model not found. Your key has access to: {', '.join(models)}"
            return "I'm having trouble connecting to my brain right now. Please try again later."

    def _mock_response(self, prompt: str) -> dict:
        # Simple mock based on keywords in prompt
        if "sector" in prompt.lower() or "schema" in prompt.lower():
            return {
                "title": "Mock Project: Sales Analysis",
                "description": "Analyze the sales data for a retail company to identify trends and opportunities. This is a MOCK response.",
                "tasks": ["Calculate total revenue", "Identify top selling products", "Analyze sales by region"],
                "schema": [
                    {"name": "transaction_id", "type": "string", "description": "Unique ID for transaction", "distribution_hint": "uuid"},
                    {"name": "date", "type": "date", "description": "Date of transaction", "distribution_hint": "last_year"},
                    {"name": "product_category", "type": "categorical", "description": "Category of product", "distribution_hint": "['Electronics', 'Clothing', 'Home']"},
                    {"name": "amount", "type": "numeric", "description": "Transaction amount", "distribution_hint": "normal(100, 20)"}
                ],
                "insights": ["Electronics have higher variance", "Sales peak in December"],
                "data_issues": ["5% missing dates", "Duplicate transaction IDs"]
            }
        return {"error": "Mock response not implemented for this prompt"}
