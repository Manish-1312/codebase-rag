"""
backend/ingest.py
==================
The main ingestion pipeline.

This is the file that ties everything together for Week 1.
Flow:
  1. Take a GitHub URL
  2. Clone the repo
  3. Chunk all files using ASTChunker
  4. Embed all chunks using OpenAI
  5. Store in Qdrant

After this runs successfully, your Qdrant collection
will have vectors for every function, class and import
block in the repo — ready to be searched.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# We use sys.path trick so imports work when running directly
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.chunker.chunker import ASTChunker
from backend.db.embedding import embed_batch
from backend.db import qudrant_client as qdb


def clone_repo(repo_url: str) -> str:
    """
    Clone a GitHub repo into a temp folder.
    --depth=1 means only get the latest commit,
    not the full history. Much faster.
    Returns the path to the cloned folder.
    """
    tmp_dir = tempfile.mkdtemp(prefix="coderag_")
    token = os.getenv("GITHUB_TOKEN", "")

    # Inject token for private repos
    if token and "github.com" in repo_url:
        repo_url = repo_url.replace("https://", f"https://{token}@")

    print(f"[ingest] Cloning {repo_url}")
    print(f"[ingest] Destination: {tmp_dir}")

    subprocess.run(
        ["git", "clone", "--depth=1", repo_url, tmp_dir],
        check=True,
        capture_output=True,
    )
    return tmp_dir


def ingest_repo(repo_url: str) -> dict:
    """
    Full pipeline — clone → chunk → embed → store.
    Returns a summary of what was indexed.
    """
    tmp_dir = None

    try:
        # Step 1 — Clone
        tmp_dir = clone_repo(repo_url)

        # Step 2 — Chunk
        print("\n[ingest] Chunking files...")
        chunker = ASTChunker(include_git_blame=False)
        chunks = chunker.chunk_directory(tmp_dir)

        if not chunks:
            return {"status": "error", "message": "No supported files found"}

        print(f"\n[ingest] Total chunks: {len(chunks)}")

        # Step 3 — Embed
        print("\n[ingest] Embedding chunks with OpenAI...")
        embed_texts = [chunk.to_embed_text() for chunk in chunks]
        vectors = embed_batch(embed_texts)

        # Pair each chunk with its vector
        chunks_with_vectors = [
            {"chunk": chunk, "vector": vector}
            for chunk, vector in zip(chunks, vectors)
        ]

        # Step 4 — Store in Qdrant
        print("\n[ingest] Storing in Qdrant...")
        client = qdb.get_client()
        qdb.ensure_collection(client)
        total = qdb.upsert_chunks(client, chunks_with_vectors)

        # Build summary
        type_counts = {}
        lang_counts = {}
        for chunk in chunks:
            type_counts[chunk.chunk_type] = type_counts.get(chunk.chunk_type, 0) + 1
            lang_counts[chunk.language]   = lang_counts.get(chunk.language,   0) + 1

        print(f"\n✅ Done! {total} chunks stored in Qdrant.")
        return {
            "status":        "success",
            "repo_url":      repo_url,
            "total_chunks":  total,
            "by_type":       type_counts,
            "by_language":   lang_counts,
            "files_scanned": len(set(c.file_path for c in chunks)),
        }

    except subprocess.CalledProcessError:
        return {"status": "error", "message": "Could not clone repo. Check the URL."}

    except Exception as e:
        return {"status": "error", "message": str(e)}

    finally:
        # Always delete the temp folder
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
            print(f"[ingest] Cleaned up temp folder")