
import os
import sys
from services.generator import project_generator

# User provided API key
API_KEY = os.getenv("GEMINI_API_KEY")

def verify_sector_adherence():
    if not API_KEY:
        print("Error: GEMINI_API_KEY environment variable not set.")
        sys.exit(1)

    print("Testing Sector Adherence for 'Fintech'...")

    history = []

    # Run a few times to check consistency
    for i in range(3):
        print(f"\n--- Generation {i+1} ---")
        try:
            context = history[-5:]
            result = project_generator.orchestrate_project_generation("Fintech", API_KEY, previous_context=context)

            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                title = result.get('title')
                company = result.get('company_name', 'Unknown')
                description = result.get('description')

                print(f"Title: {title}")
                print(f"Company: {company}")
                print(f"Description: {description}")

                # Check for keywords that indicate strict adherence
                keywords = ["payment", "bank", "loan", "invest", "crypto", "transaction", "finance", "wallet", "ledger"]
                is_fintech = any(k in description.lower() for k in keywords)
                print(f"Is Fintech-related? {'Yes' if is_fintech else 'Warning: Check Description'}")

                # Update history
                new_item = f"{title} ({company})"
                history.append(new_item)

        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    verify_sector_adherence()
