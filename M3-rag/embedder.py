"""
Embedding pipeline for RAG using BGE-M3 via Ollama.
Reads chunks.jsonl, adds embedding vectors, writes chunks_embedded.jsonl,
then saves embeddings to PostgreSQL with pgvector.

Usage: python embedder.py

Requires:
  - Ollama running locally (http://localhost:11434)
  - bge-m3 model pulled: ollama pull bge-m3
  - PostgreSQL with pgvector on DATABASE_URL from .env
  - psycopg2 installed
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# PostgreSQL configuration
# ---------------------------------------------------------------------------

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("Install psycopg2: pip install psycopg2-binary")
    raise

ENV_PATH = Path(__file__).resolve().parent / ".env"

def load_env(path: Path) -> dict:
    """Parse simple KEY=VAL .env file."""
    env = {}
    if path.exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env

def build_db_url(env: dict) -> str:
    """Build DATABASE_URL from individual params, or return DATABASE_URL if present."""
    if "DATABASE_URL" in env:
        return env["DATABASE_URL"]
    user = env.get("POSTGRES_USER", "postgres")
    pwd = env.get("POSTGRES_PASSWORD", "")
    host = env.get("POSTGRES_HOST", "127.0.0.1")
    port = env.get("POSTGRES_PORT", "5432")
    db = env.get("POSTGRES_DB", "postgres")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"

env = load_env(ENV_PATH)
DB_URL = os.getenv("DATABASE_URL", build_db_url(env))
PG_BATCH = 100

OLLAMA_URL = "http://localhost:11434/api/embed"
MODEL = "bge-m3"
BATCH_SIZE = 32          # max texts per Ollama request
INPUT_PATH = Path(__file__).resolve().parent / "chunks.jsonl"
EMBEDDED_PATH = Path(__file__).resolve().parent / "chunks_embedded.jsonl"
STATE_PATH = Path(__file__).resolve().parent / ".embed_progress.json"


def load_chunks(path: Path) -> list:
    """Load chunks from JSONL file."""
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def load_progress(path: Path) -> set:
    """Load set of already-embedded chunk_ids from state file."""
    if not path.exists():
        return set()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("done", []))


def save_progress(path: Path, done_ids: set):
    """Save embedded chunk_ids to state file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"done": list(done_ids)}, f)


def call_ollama(texts: list, max_retries: int = 3) -> list:
    """
    Call Ollama /api/embed endpoint.
    Returns list of embedding vectors (list of floats) aligned with input texts.
    """
    payload = json.dumps({"model": MODEL, "input": texts}).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["embeddings"]
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Ollama embed failed after {max_retries} retries: {e}")
            wait = 2 ** attempt
            time.sleep(wait)


def embed_chunks(chunks: list, batch_size: int = BATCH_SIZE) -> list:
    """
    Embed all chunks via Ollama BGE-M3.
    Supports resumable runs via .embed_progress.json.
    Prints progress to stdout.
    """
    done_ids = load_progress(STATE_PATH)
    total = len(chunks)
    batch_count = 0
    batch_texts = []
    batch_indices = []

    for i, chunk in enumerate(chunks):
        cid = chunk["metadata"]["chunk_id"]
        if cid in done_ids or "embedding" in chunk:
            print(f"  [{i+1}/{total}] SKIP {cid[:60]}...")
            continue
        batch_texts.append(chunk["text"])
        batch_indices.append(i)
        batch_count += 1

        if batch_count >= batch_size:
            flush_batch(chunks, batch_indices, batch_texts, done_ids)
            batch_count = 0
            batch_texts = []
            batch_indices = []

    # Flush remaining
    if batch_texts:
        flush_batch(chunks, batch_indices, batch_texts, done_ids)

    # Final summary
    embedded_count = sum(1 for c in chunks if "embedding" in c)
    skipped_count = total - embedded_count
    print(f"\nDone: {embedded_count} embedded, {skipped_count} skipped, {total} total")
    return chunks


def flush_batch(chunks: list, indices: list, texts: list, done_ids: set):
    """Embed one batch and write vectors into chunks."""
    idx_strs = [f"#{i}" for i in indices]
    print(f"  embedding batch {', '.join(idx_strs)} ({len(texts)} texts) ...")
    embeddings = call_ollama(texts)
    for idx, vec in zip(indices, embeddings):
        chunks[idx]["embedding"] = vec
        done_ids.add(chunks[idx]["metadata"]["chunk_id"])
    save_progress(STATE_PATH, done_ids)


def write_output(chunks: list, path: Path):
    """Write embedded chunks to JSONL."""
    count = 0
    with open(path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            if "embedding" in chunk:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                count += 1
    print(f"Wrote {count} embedded chunks → {path}")


# ---------------------------------------------------------------------------
# PostgreSQL persistence
# ---------------------------------------------------------------------------

def ensure_pgvector_table(cur):
    """Create the chunks table with pgvector column if it doesn't exist."""
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rag_chunks (
            chunk_id       TEXT PRIMARY KEY,
            source_file    TEXT,
            file_path      TEXT,
            doc_type       TEXT,
            title          TEXT,
            section_heading TEXT,
            parent_headings TEXT[],
            language       TEXT,
            keywords       TEXT[],
            summary        TEXT,
            token_count_approx INTEGER,
            text           TEXT,
            embedding      VECTOR(1024),
            created_at     TIMESTAMPTZ DEFAULT NOW()
        );
    """)


def save_to_postgres(chunks: list, db_url: str) -> int:
    """
    Save embedded chunks to PostgreSQL with pgvector.
    Returns the number of rows inserted/updated.
    """
    if not db_url:
        print("No DATABASE_URL — skipping PostgreSQL save.")
        return 0

    embedded = [c for c in chunks if "embedding" in c]
    if not embedded:
        print("No embedded chunks to save.")
        return 0

    conn = psycopg2.connect(db_url)
    try:
        cur = conn.cursor()
        ensure_pgvector_table(cur)
        conn.commit()

        # Create indexes if they don't exist
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding ON rag_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_doctype ON rag_chunks USING btree (doc_type);")
        conn.commit()

        values = []
        for c in embedded:
            md = c["metadata"]
            values.append((
                c["metadata"]["chunk_id"],
                c["metadata"]["source_file"],
                c["metadata"]["file_path"],
                c["metadata"]["doc_type"],
                c["metadata"]["title"],
                c["metadata"]["section_heading"],
                c["metadata"]["parent_headings"],
                c["metadata"]["language"],
                c["metadata"]["keywords"],
                c["metadata"]["summary"],
                c["metadata"]["token_count_approx"],
                c["text"],
                c["embedding"],
            ))

        cols = (
            "chunk_id, source_file, file_path, doc_type, title, "
            "section_heading, parent_headings, language, keywords, "
            "summary, token_count_approx, text, embedding"
        )

        query = f"""
            INSERT INTO rag_chunks ({cols})
            VALUES %s
            ON CONFLICT (chunk_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                text = EXCLUDED.text,
                source_file = EXCLUDED.source_file,
                file_path = EXCLUDED.file_path,
                doc_type = EXCLUDED.doc_type,
                title = EXCLUDED.title,
                section_heading = EXCLUDED.section_heading,
                parent_headings = EXCLUDED.parent_headings,
                language = EXCLUDED.language,
                keywords = EXCLUDED.keywords,
                summary = EXCLUDED.summary,
                token_count_approx = EXCLUDED.token_count_approx,
                created_at = NOW();
        """

        execute_values(cur, query, values, page_size=PG_BATCH)
        conn.commit()
        print(f"Saved {len(values)} embeddings to PostgreSQL (rag_chunks)")
        return len(values)
    finally:
        conn.close()


def main():
    if not INPUT_PATH.exists():
        print(f"Error: {INPUT_PATH} not found. Run chunker.py first.")
        raise SystemExit(1)

    if not DB_URL:
        print("Warning: DATABASE_URL not set. Skipping PostgreSQL.")

    # Verify Ollama connectivity
    try:
        health = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        models = json.loads(health.read().decode("utf-8")).get("models", [])
        model_names = [m["name"] for m in models]
        if MODEL not in model_names and not any(MODEL in m for m in model_names):
            print(f"Warning: model '{MODEL}' not found in Ollama.")
            print(f"Available: {', '.join(model_names)}")
            print(f"Run: ollama pull {MODEL}")
            raise SystemExit(1)
        print(f"Ollama OK — model '{MODEL}' is available")
    except (urllib.error.URLError, TimeoutError):
        print("Error: Cannot reach Ollama at http://localhost:11434")
        print("Make sure Ollama is running: ollama serve")
        raise SystemExit(1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"\n=== Embedding pipeline started at {now} ===")
    print(f"Model: {MODEL}")
    print(f"Input: {INPUT_PATH}")
    print(f"Output: {EMBEDDED_PATH}")
    print(f"Database: {DB_URL.split('@')[-1] if DB_URL else '(not set)'}")

    chunks = load_chunks(INPUT_PATH)
    print(f"Loaded {len(chunks)} chunks")

    chunks = embed_chunks(chunks)

    write_output(chunks, EMBEDDED_PATH)

    save_to_postgres(chunks, DB_URL)

    # Clean up progress file on successful completion
    if STATE_PATH.exists():
        STATE_PATH.unlink()
        print("Cleaned up .embed_progress.json")


if __name__ == "__main__":
    main()
