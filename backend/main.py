"""
backend/main.py
================
FastAPI server — the HTTP layer.

Endpoints:
  POST /ingest   → give it a GitHub URL, indexes the repo
  POST /query    → ask a question, get a cited answer
  GET  /stats    → how many chunks are stored
  GET  /health   → is the server alive?

Run locally:
  uvicorn backend.main:app --reload --port 8000
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

from backend.ingest import ingest_repo
from backend.agent.agent import ask
from backend.db import qudrant_client as qdb

app = FastAPI(
    title="Codebase RAG API",
    description="Agentic RAG over GitHub codebases",
    version="1.0.0",
)

# Allow React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000","http://localhost:5174","https://codebase-rag-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request models ────────────────────────────────────────────

class IngestRequest(BaseModel):
    repo_url: str        # "https://github.com/owner/repo"
    private: bool = False


class QueryRequest(BaseModel):
    question: str        # "How does backpropagation work?"


# ── Endpoints ─────────────────────────────────────────────────

@app.get("/health")
def health():
    """Simple check — is the server running?"""
    return {"status": "ok"}


@app.get("/stats")
def stats():
    """
    Returns how many chunks are stored in Qdrant.
    Shown in the frontend topbar.
    """
    try:
        client = qdb.get_client()
        return qdb.get_collection_stats(client)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
def ingest(req: IngestRequest):
    """
    Clone a GitHub repo and index all code into Qdrant.
    Takes 30-60 seconds depending on repo size.
    """
    try:
        result = ingest_repo(req.repo_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
def query(req: QueryRequest):
    """
    Ask a question about the indexed codebase.
    The agent searches Qdrant and returns a cited answer.
    """
    try:
        result = ask(req.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))