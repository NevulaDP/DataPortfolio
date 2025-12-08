# Junior Data Analyst Portfolio Builder

This project is a web application designed to help Junior Data Analysts and BI professionals create projects and build a portfolio. It is built using **Streamlit**.

## Architecture

- **Framework**: Streamlit
- **Logic**: Python
  - Generates synthetic datasets using `Faker` and LLM guidance (Gemini).
  - Provides a "Senior Agent" chatbot powered by Gemini.
  - Executes SQL using `sqlite3` (in-memory).
  - Executes Python using `pandas` on the server (restricted context).

## Setup & Running

### Prerequisites
- Python 3.12+
- Gemini API Key (Optional, for real AI responses)

### Local Setup
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your API key (optional):
   ```bash
   export GEMINI_API_KEY="your_key_here"
   ```
4. Run the application:
   ```bash
   streamlit run app.py
   ```

### Docker Deployment
1. Build the image:
   ```bash
   docker build -t portfolio-builder .
   ```
2. Run the container:
   ```bash
   docker run -p 8501:8501 -e GEMINI_API_KEY="your_key_here" portfolio-builder
   ```

## Security Note
This application executes user-submitted Python code on the server side. It is intended for local use or controlled environments (like a personal portfolio container). Do not deploy publicly without additional sandboxing.
