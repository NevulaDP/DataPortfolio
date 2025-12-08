import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class LLMService:
    def __init__(self):
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.has_key = True
        else:
            self.has_key = False
            print("Warning: GEMINI_API_KEY not found. Using mock mode.")

    def generate_json(self, prompt: str) -> dict:
        if not self.has_key:
            return self._mock_response(prompt)

        try:
            # Force JSON response structure
            full_prompt = f"{prompt}\n\nRespond strictly with valid JSON."
            response = self.model.generate_content(full_prompt)
            # Simple cleaning of markdown code blocks if present
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            print(f"Error calling Gemini: {e}")
            return self._mock_response(prompt)

    def generate_text(self, prompt: str) -> str:
        if not self.has_key:
            return "This is a mock response from the Senior Agent. Please set GEMINI_API_KEY to get real responses."

        try:
            response = self.model.generate_content(prompt)
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

llm_service = LLMService()
