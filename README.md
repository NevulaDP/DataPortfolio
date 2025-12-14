# Junior Data Analyst Portfolio Builder

This project is a web application designed to help Junior Data Analysts and BI professionals create projects and build a portfolio. It is built using **Streamlit**.

## Features

*   **Synthetic Project Generation**: Generates realistic business scenarios and datasets based on a chosen sector.
*   **Integrated Workspace**: A unified notebook environment supporting Python, SQL (DuckDB), and Markdown.
*   **AI Mentorship**: A built-in "Senior Data Analyst" chatbot powered by Gemini to guide you through your analysis.
*   **Save & Load Sessions**: Persist your work (including the full dataset, code, and chat history) to a JSON file and restore it later.
*   **Report Generation**: Export your analysis as a polished HTML report.

## Architecture

- **Framework**: Streamlit
- **Logic**: Python
  - Generates synthetic datasets using `Faker` and LLM guidance (Gemini).
  - Provides a "Senior Agent" chatbot powered by Gemini.
  - Executes SQL using `duckdb`.
  - Executes Python using `pandas` on the server (restricted context).
  - **Session Management**: Serializes full session state (project definition, notebook cells, chat history, and DataFrame) to JSON for portability.

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

## Usage Guide

### Saving and Loading
*   **Save Session**: Once inside a workspace, use the **Save Session** button in the sidebar to download your entire session as a `.json` file.
*   **Load Session**: Use the **Load Session** file uploader in the sidebar (available on the landing page or workspace) to restore your previous work.
    *   *Note: Loading a session restores your code and data but resets the active Python variables. You will need to re-run your notebook cells to regenerate plots and variable states.*

## Security Note
This application executes user-submitted Python code on the server side. It is intended for local use or controlled environments (like a personal portfolio container). Do not deploy publicly without additional sandboxing.
