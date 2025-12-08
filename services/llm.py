
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class LLMService:
    def __init__(self):
        pass

    def _get_model(self, api_key: str):
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-2.5-flash')

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
            full_prompt = f"{prompt}\n\nRespond strictly with valid JSON."
            response = model.generate_content(full_prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            # If an API key was provided, we want to see the REAL error, not the mock.
            if key_to_use:
                return {"error": f"API Error: {str(e)}"}
            return self._mock_response(prompt)

    def generate_text(self, prompt: str, api_key: str = None, code_context: dict = None) -> str:
        key_to_use = api_key or os.getenv("GEMINI_API_KEY")
        if not key_to_use:
            return "This is a mock response from the Senior Agent. Please set GEMINI_API_KEY to get real responses."

        try:
            model = self._get_model(key_to_use)

            # Construct context string
            code_str = ""
            if code_context:
                code_str = "\n\n--- User's Current Code ---\n"
                if code_context.get("python"):
                    code_str += f"Python IDE:\n{code_context['python']}\n\n"
                if code_context.get("sql"):
                    code_str += f"SQL IDE:\n{code_context['sql']}\n"
                code_str += "---------------------------\n"

            # Add system instruction to prompt for Socratic guidance with code awareness
            system_instruction = """
            You are a Senior Data Analyst mentor guiding a Junior Analyst.
            You have access to the code they are currently writing in the IDE (if any).

            Guidelines:
            1. If the user asks a direct question like "Will this code work?" or "What is wrong?", analyze the provided code context.
               - If there is a syntax error or logical flaw, point it out specifically.
               - If it looks correct, confirm it.
            2. If the user is asking for the solution from scratch (e.g., "How do I do X?"), DO NOT provide the full code immediately.
               - Instead, guide them: "Have you tried using groupby?" or "Look into the matplotlib plot function."
               - Ask leading questions to help them derive the answer.
            3. Balance being helpful (unblocking them) with being educational (making them think).
               - If they are clearly stuck after trying, you can provide a small snippet or corrected syntax, but avoid writing the whole script if possible.
            4. Be encouraging and constructive.
            """
            full_prompt = f"{system_instruction}\n{code_str}\nUser Question: {prompt}"

            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            if key_to_use:
                return f"Error connecting to AI Mentor: {str(e)}"
            return "I'm having trouble connecting to my brain right now. Please try again later."

    def _mock_response(self, prompt: str) -> dict:
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
