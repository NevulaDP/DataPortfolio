
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
        # Configure a new client with the specific API key
        # Note: genai.configure() sets global state, which is bad for concurrency.
        # However, the library doesn't easily expose a way to pass api_key per request
        # without diving into lower-level clients.
        # A workaround for simple apps is to just configure it before use, but strictly speaking
        # this is not thread-safe.
        # BUT, for this task, we will attempt to limit the scope or assume single-threaded for now,
        # OR better: check if we can pass request_options to generate_content.

        # Looking at library source, configure() updates `_client_manager`.
        # We should try to use `client_options` if possible.

        # If we can't solve the thread-safety of the library easily, we will document it.
        # But let's try to do it right.

        # Re-configuring globally is the only documented way for the high-level API.
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-1.5-flash')

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
            return self._mock_response(prompt)

    def generate_text(self, prompt: str, api_key: str = None) -> str:
        key_to_use = api_key or os.getenv("GEMINI_API_KEY")
        if not key_to_use:
            return "This is a mock response from the Senior Agent. Please set GEMINI_API_KEY to get real responses."

        try:
            model = self._get_model(key_to_use)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error calling Gemini: {e}")
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

# Export the class, not the instance
