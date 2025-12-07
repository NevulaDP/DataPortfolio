from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.generator import project_generator
from services.llm import llm_service
import pandas as pd
import io
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProjectRequest(BaseModel):
    sector: str

class ChatRequest(BaseModel):
    message: str
    context: str = ""

@app.post("/api/generate_project")
async def generate_project(req: ProjectRequest):
    try:
        # 1. Generate Definition
        definition = project_generator.generate_project_definition(req.sector)

        # 2. Generate Data
        df = project_generator.generate_dataset(definition.get('schema', []), rows=500)

        # 3. Convert Data to JSON/CSV friendly format for frontend
        # We'll send data as a list of records for easy consumption by frontend grid/sql.js
        data_json = df.to_json(orient='records', date_format='iso')

        return {
            "definition": definition,
            "data": json.loads(data_json)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        prompt = f"You are a Senior Data Analyst mentor. The user is a Junior Analyst working on a project.\nContext: {req.context}\n\nUser: {req.message}\nMentor:"
        response = llm_service.generate_text(prompt)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
