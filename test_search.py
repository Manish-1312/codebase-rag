# save as test_search.py in project root
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from backend.db.embedding import embed_text
from backend.db import qudrant_client as qdb

# Ask a question in plain English
question = "how does backpropagation work?"

print(f"Question: {question}")
print("Searching...\n")

query_vector = embed_text(question)
client = qdb.get_client()
results = qdb.search_chunks(client, query_vector, top_k=3)

for i, chunk in enumerate(results):
    print(f"Result #{i+1}")
    print(f"  Name      : {chunk['name']}")
    print(f"  Type      : {chunk['chunk_type']}")
    print(f"  File      : {chunk['file_path'].split('/')[-1]}")
    print(f"  Lines     : {chunk['start_line']} → {chunk['end_line']}")
    print(f"  Score     : {chunk['score']}")
    print(f"  Code      :\n{chunk['raw_code'][:200]}")
    print()