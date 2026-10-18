"""
backend/db/qdrant_client.py
============================
Everything related to Qdrant:
- Create the collection (one-time setup)
- Insert chunks (upsert = insert or update)
- Search by vector similarity
- Delete chunks for a file (used by webhook)
"""

import hashlib
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)
from dotenv import load_dotenv
import os

load_dotenv()

# Embedding size for text-embedding-3-small
VECTOR_SIZE = 1536


def get_client() -> QdrantClient:
    """Create and return a Qdrant Cloud client."""
    return QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )


def ensure_collection(client: QdrantClient) -> None:
    """
    Create the collection if it doesn't exist yet.
    Safe to call every time — won't delete existing data.
    
    A collection in Qdrant is like a table in a database.
    It stores all our code chunks as vectors.
    """
    collection_name = os.getenv("QDRANT_COLLECTION", "codebase_chunks")
    existing = [c.name for c in client.get_collections().collections]
    
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
                # COSINE measures angle between vectors
                # Perfect for semantic similarity
                # Two similar texts → small angle → high score
            ),
        )
        print(f"[qdrant] Created collection: {collection_name}")
    else:
        print(f"[qdrant] Collection exists: {collection_name}")


def chunk_id_to_int(chunk_id: str) -> int:
    """
    Qdrant needs integer IDs for each point.
    We hash the chunk_id string into a stable integer.
    
    Same chunk_id always gives same integer — so
    re-indexing the same file updates the point
    instead of creating a duplicate.
    """
    return int(hashlib.md5(chunk_id.encode()).hexdigest(), 16) % (10**15)


def upsert_chunks(client: QdrantClient, chunks_with_vectors: list[dict]) -> int:
    """
    Insert or update chunks in Qdrant.
    
    Each item in chunks_with_vectors is:
    {
        "chunk": CodeChunk object,
        "vector": list of 1536 floats
    }
    
    Upsert means: if the point already exists → update it.
    If it doesn't exist → create it.
    This makes re-indexing safe — no duplicates.
    """
    collection_name = os.getenv("QDRANT_COLLECTION", "codebase_chunks")
    points = []

    for item in chunks_with_vectors:
        chunk = item["chunk"]
        vector = item["vector"]

        point = PointStruct(
            id=chunk_id_to_int(chunk.chunk_id),
            vector=vector,
            payload={
                # Everything stored alongside the vector
                # This is what comes back when we search
                "chunk_id":     chunk.chunk_id,
                "chunk_type":   chunk.chunk_type,
                "language":     chunk.language,
                "file_path":    chunk.file_path,
                "start_line":   chunk.start_line,
                "end_line":     chunk.end_line,
                "name":         chunk.name,
                "signature":    chunk.signature,
                "docstring":    chunk.docstring,
                "raw_code":     chunk.raw_code,
                "dependencies": chunk.dependencies,
                "git_author":   chunk.git_author,
            },
        )
        points.append(point)

    # Insert in batches of 100
    total = 0
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch,
            wait=True
        )
        total += len(batch)
        print(f"  [qdrant] inserted {total}/{len(points)} chunks...")

    return total


def search_chunks(
    client: QdrantClient,
    query_vector: list[float],
    top_k: int = 8,
) -> list[dict]:
    """Find the most similar chunks to a query vector."""
    collection_name = os.getenv("QDRANT_COLLECTION", "codebase_chunks")

    response = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    )

    return [
        {**hit.payload, "score": round(hit.score, 4)}
        for hit in response.points  # ← just use .points directly
    ]

def delete_file_chunks(client: QdrantClient, file_path: str) -> None:
    """
    Delete all chunks from a specific file.
    Called when a file changes — delete old, insert fresh.
    """
    collection_name = os.getenv("QDRANT_COLLECTION", "codebase_chunks")
    client.delete(
        collection_name=collection_name,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="file_path",
                    match=MatchValue(value=file_path),
                )
            ]
        ),
    )
    print(f"[qdrant] Deleted chunks for: {file_path}")


def get_collection_stats(client: QdrantClient) -> dict:
    """Basic stats — shown in the frontend topbar."""
    collection_name = os.getenv("QDRANT_COLLECTION", "codebase_chunks")
    info = client.get_collection(collection_name)
    return {
        "total_chunks": info.points_count,
        "collection":   collection_name,
        "status":       str(info.status),
    }