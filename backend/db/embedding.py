"""
backend/db/embeddings.py
=========================
Converts text into vectors using OpenAI's embedding model.

What is an embedding?
A vector is just a list of numbers — e.g. [0.23, -0.81, 0.45, ...]
OpenAI's model converts any text into 1536 numbers.
Similar texts get similar number patterns.
That's how semantic search works — find chunks whose
numbers are closest to the query's numbers.
"""

import time
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv
import os

load_dotenv()

# Create one shared OpenAI client
_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
def embed_text(text: str) -> list[float]:
    """
    Embed a single string.
    Used at query time — when user asks a question,
    we embed the question to search against Qdrant.
    
    @retry means: if OpenAI fails (rate limit, timeout),
    automatically try again up to 3 times.
    Waits 2s after 1st fail, 4s after 2nd, 8s after 3rd.
    """
    response = _client.embeddings.create(
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        input=text,
    )
    return response.data[0].embedding


def embed_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """
    Embed a list of strings.
    Used during ingestion — embed all chunks at once.
    
    Why batches of 100?
    OpenAI allows 2048 per request but we use 100 to:
    - Stay within rate limits
    - Show progress
    - Recover easily if one batch fails
    """
    all_vectors = []
    total_batches = (len(texts) + batch_size - 1) // batch_size

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        print(f"  [embed] batch {batch_num}/{total_batches} "
              f"({len(batch)} texts)...")

        response = _client.embeddings.create(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            input=batch,
        )

        # Results come back in the same order we sent them
        vectors = [item.embedding for item in response.data]
        all_vectors.extend(vectors)

        # Small pause between batches to respect rate limits
        if i + batch_size < len(texts):
            time.sleep(0.5)

    return all_vectors