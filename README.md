# Junior Data Analyst Portfolio Builder

This project is a web application designed to help Junior Data Analysts and BI professionals create projects and build a portfolio.

## Architecture

- **Backend**: FastAPI (Python)
  - Generates synthetic datasets using `Faker` and LLM guidance (Gemini).
  - Provides a "Senior Agent" chatbot powered by Gemini.
- **Frontend**: React (TypeScript, Vite)
  - Workspace with Python and SQL editors.
  - In-browser code execution using `Pyodide` (Python) and `sql.js` (SQL).
  - Chat interface for guidance.

## Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
