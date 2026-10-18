"""
backend/agent/tools.py
=======================
Tools available to the LangGraph agent.

What is a tool?
A tool is just a function the agent can CHOOSE to call.
The agent reads the tool's description and decides:
"Should I use this tool to answer the question?"

We have two tools right now:
1. search_code    — search Qdrant for relevant chunks
2. get_file_code  — get all chunks from a specific file
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_core.tools import tool
from dotenv import load_dotenv
load_dotenv()

from backend.db.embedding import embed_text
from backend.db import qudrant_client as qdb


@tool
def search_code(query: str) -> str:
    """
    Search the codebase for code relevant to a question.
    Use this when the user asks HOW something works,
    WHERE something is handled, or WHAT a function does.
    Input should be a clear search query describing what to find.
    """
    try:
        query_vector = embed_text(query)
        client = qdb.get_client()
        results = qdb.search_chunks(client, query_vector, top_k=5)

        if not results:
            return "No relevant code found for this query."

        # Format results as readable text for the agent
        output = []
        for i, chunk in enumerate(results):
            file_name = chunk['file_path'].split('/')[-1]
            output.append(
                f"[Result {i+1}]\n"
                f"Name: {chunk['name']}\n"
                f"Type: {chunk['chunk_type']}\n"
                f"File: {file_name}\n"
                f"Lines: {chunk['start_line']} → {chunk['end_line']}\n"
                f"Score: {chunk['score']}\n"
                f"Code:\n{chunk['raw_code']}\n"
            )

        return "\n---\n".join(output)

    except Exception as e:
        return f"Search failed: {str(e)}"


@tool
def get_file_code(file_name: str) -> str:
    """
    Get all code chunks from a specific file.
    Use this when the user asks about a specific file,
    or when you need full context from one file.
    Input should be the file name e.g. 'engine.py'
    """
    try:
        # Search using the file name as query
        query_vector = embed_text(f"code in file {file_name}")
        client = qdb.get_client()
        results = qdb.search_chunks(client, query_vector, top_k=20)

        # Filter to only chunks from that file
        file_chunks = [
            r for r in results
            if file_name.lower() in r['file_path'].lower()
        ]

        if not file_chunks:
            return f"No chunks found for file: {file_name}"

        output = []
        for chunk in file_chunks:
            output.append(
                f"Name: {chunk['name']}\n"
                f"Lines: {chunk['start_line']} → {chunk['end_line']}\n"
                f"Code:\n{chunk['raw_code']}\n"
            )

        return f"File: {file_name}\n\n" + "\n---\n".join(output)

    except Exception as e:
        return f"Failed to get file: {str(e)}"