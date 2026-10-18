"""
run_ingest.py
=============
Run this to test the full Week 1 pipeline.

Usage:
    python run_ingest.py
"""

from backend.ingest import ingest_repo

# Use any small public GitHub repo for testing
# This one is a small Python project — good for testing
REPO_URL = "https://github.com/karpathy/micrograd"

print("=" * 50)
print("Agentic RAG — Week 1 Ingestion Test")
print("=" * 50)

result = ingest_repo(REPO_URL)

print("\n" + "=" * 50)
print("RESULT:")
for key, value in result.items():
    print(f"  {key}: {value}")
print("=" * 50)