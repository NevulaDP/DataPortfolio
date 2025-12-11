
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
        # Using gemma-3-27b-it as explicitly requested
        return genai.GenerativeModel('gemma-3-27b-it')

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

    def generate_text(self, prompt: str, api_key: str = None, project_context: dict = None, code_context: dict = None, history: list = None) -> str:
        """
        Generates text response from the LLM.

        Args:
            prompt (str): The user's current question/prompt.
            api_key (str): The API key to use.
            project_context (dict): The project definition (title, description, tasks, schema).
            code_context (dict): The current state of the python/sql editors.
            history (list): List of message dictionaries [{'role': 'user'|'assistant', 'content': '...'}] from the session state.
        """
        key_to_use = api_key or os.getenv("GEMINI_API_KEY")
        if not key_to_use:
            return "This is a mock response from the Senior Agent. Please set GEMINI_API_KEY to get real responses."

        try:
            model = self._get_model(key_to_use)

            # Construct project context string
            project_str = ""
            if project_context:
                project_str = "\n\n--- Project Context ---\n"
                project_str += f"Title: {project_context.get('title', 'N/A')}\n"
                project_str += f"Scenario: {project_context.get('description', 'N/A')}\n"
                if 'tasks' in project_context:
                    project_str += "Tasks:\n"
                    for i, task in enumerate(project_context['tasks']):
                        project_str += f"{i+1}. {task}\n"

                schema = project_context.get('display_schema') or project_context.get('schema')
                if schema:
                     project_str += "Schema:\n"
                     for col in schema:
                         project_str += f"- {col.get('name')} ({col.get('type')})\n"

                project_str += "-----------------------\n"

            # Construct context string from code
            code_str = ""
            if code_context:
                code_str = "\n\n--- User's Current Notebook ---\n"

                # Handle Notebook List Format
                if code_context.get("notebook"):
                    for idx, cell in enumerate(code_context["notebook"]):
                        c_type = cell.get('cell_type', 'unknown').upper()
                        content = cell.get('source', '').strip()
                        output = str(cell.get('output', '')).strip()

                        code_str += f"Cell {idx+1} [{c_type}]:\n{content}\n"
                        if output:
                            # Truncate output if it's too long to avoid token limits
                            if len(output) > 500:
                                output = output[:500] + "...(truncated)"
                            code_str += f"Output:\n{output}\n"
                        code_str += "\n"

                # Fallback for legacy keys (if any)
                if code_context.get("python"):
                    code_str += f"Python IDE:\n{code_context['python']}\n\n"
                if code_context.get("sql"):
                    code_str += f"SQL IDE:\n{code_context['sql']}\n"

                code_str += "---------------------------\n"

            # Construct conversation history string
            history_str = ""
            if history:
                history_str = "\n\n--- Conversation History ---\n"
                # Limit history to last 10 messages to prevent token overflow
                recent_history = history[-10:]
                for msg in recent_history:
                    role = "User" if msg['role'] == 'user' else "Mentor"
                    content = msg['content']
                    history_str += f"{role}: {content}\n"
                history_str += "----------------------------\n"

            # Add system instruction to prompt for Socratic guidance with code awareness
            system_instruction = """
            You are a Senior Data Analyst mentor guiding a Junior Analyst.
            You have access to the code they are currently writing in the IDE (if any) and the recent conversation history.

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

            full_prompt = f"{system_instruction}\n{project_str}\n{code_str}\n{history_str}\nUser Question: {prompt}"

            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            if key_to_use:
                return f"Error connecting to AI Mentor: {str(e)}"
            return "I'm having trouble connecting to my brain right now. Please try again later."

    def _mock_response(self, prompt: str) -> dict:
        return {
            "title": "Mock Project: Tech & Retail Analysis (Enhanced Mock)",
            "description": "Analyze sales trends for 'GadgetWorld', a tech retailer facing stagnant growth. This is a MOCK response designed to show realistic data examples.",
            "tasks": ["Calculate revenue share by Product Model", "Analyze the relationship between Price and Warranty uptake", "Identify refund trends"],
            "recipe": {
                "anchor_entity": {
                    "name": "Product Model",
                    "options": ["Sony WH-1000XM5", "MacBook Air M2", "Samsung Galaxy S23", "Kindle Paperwhite", "Logitech MX Master 3"],
                    "weights": [0.2, 0.15, 0.25, 0.2, 0.2]
                },
                "correlated_columns": [
                    {
                        "name": "Price",
                        "type": "numeric",
                        "rules": {
                            "Sony WH-1000XM5": {"min": 250, "max": 350},
                            "MacBook Air M2": {"min": 900, "max": 1200},
                            "Samsung Galaxy S23": {"min": 700, "max": 900},
                            "Kindle Paperwhite": {"min": 100, "max": 140},
                            "Logitech MX Master 3": {"min": 80, "max": 100},
                            "default": {"min": 50, "max": 1000}
                        }
                    },
                    {
                        "name": "Warranty Purchased",
                        "type": "boolean",
                        "rules": {
                            "Sony WH-1000XM5": 0.2,
                            "MacBook Air M2": 0.4,
                            "Samsung Galaxy S23": 0.3,
                            "Kindle Paperwhite": 0.1,
                            "Logitech MX Master 3": 0.05
                        }
                    }
                ],
                "faker_columns": [
                    {"name": "Transaction ID", "faker_method": "uuid4"},
                    {"name": "Customer Name", "faker_method": "name"},
                    {"name": "Purchase Date", "faker_method": "date_this_year"},
                    {"name": "Store City", "faker_method": "city"}
                ]
            },
            "display_schema": [
                {"name": "Product Model", "type": "Categorical", "description": "Specific product name"},
                {"name": "Price", "type": "Numeric", "description": "Sales price in USD"},
                {"name": "Warranty Purchased", "type": "Boolean", "description": "If extended warranty was bought"},
                {"name": "Transaction ID", "type": "String", "description": "Unique transaction key"},
                {"name": "Customer Name", "type": "String", "description": "Buyer name"},
                {"name": "Purchase Date", "type": "Date", "description": "Date of purchase"},
                {"name": "Store City", "type": "String", "description": "City where store is located"}
            ]
        }
