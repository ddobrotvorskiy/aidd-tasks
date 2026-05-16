"""
Query script for M3-rag semantic search.
Embeds a query via Ollama bge-m3, does cosine similarity search in Postgres pgvector,
returns top-K results with metadata.

Usage:
    python query.py                              # interactive / demo with 3 test queries
    python query.py "your query"                 # single query, default top_k=5
    python query.py "your query" 10              # single query, top_k=10
    python query.py "your query" 5 --type adr    # single query with doc_type filter
    python query.py "your query" 5 --source adr-001-mongodb-vs-postgres.md  # filter by source
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants (mirror embedder.py)
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
MODEL = "bge-m3"
OLLAMA_URL = "http://localhost:11434/api/embed"

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Install psycopg2: pip install psycopg2-binary")
    raise

# ---------------------------------------------------------------------------
# .env loader (re-use logic from embedder.py)
# ---------------------------------------------------------------------------

def load_env(path: Path) -> dict:
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
    if "DATABASE_URL" in env:
        return env["DATABASE_URL"]
    user = env.get("POSTGRES_USER", "postgres")
    pwd = env.get("POSTGRES_PASSWORD", "")
    host = env.get("POSTGRES_HOST", "127.0.0.1")
    port = env.get("POSTGRES_PORT", "5432")
    db = env.get("POSTGRES_DB", "postgres")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"

_env = load_env(PROJECT_ROOT / ".env")
DB_URL = build_db_url(_env)

# ---------------------------------------------------------------------------
# Core: embed a query via Ollama
# ---------------------------------------------------------------------------

def embed_query(text: str) -> list[float]:
    """Embed a single query string using the same bge-m3 model used for ingestion."""
    payload = json.dumps({"model": MODEL, "input": [text]}).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["embeddings"][0]

# ---------------------------------------------------------------------------
# Core: cosine similarity search in pgvector
# ---------------------------------------------------------------------------

def search(
    query: str,
    top_k: int = 5,
    doc_type: str | None = None,
    source_file: str | None = None,
) -> list[dict]:
    """
    Embed query, run cosine similarity search against rag_chunks table,
    optionally filtered by doc_type and/or source_file.

    Returns list of dicts with:
        score, chunk_id, source_file, doc_type, title, section_heading, text (truncated)
    """
    query_vec = embed_query(query)

    conds = []
    where_params: list = []

    if doc_type:
        conds.append("doc_type = %s")
        where_params.append(doc_type)

    if source_file:
        conds.append("source_file = %s")
        where_params.append(source_file)

    where = ""
    if conds:
        where = "WHERE " + " AND ".join(conds)

    sql = f"""
        SELECT
            chunk_id,
            source_file,
            file_path,
            doc_type,
            title,
            section_heading,
            text,
            1 - (embedding <=> %s::vector) AS similarity
        FROM rag_chunks
        {where}
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """
    params = [query_vec] + where_params + [query_vec, top_k]

    conn = psycopg2.connect(DB_URL)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        text = row[6]
        results.append({
            "score": round(float(row[7]), 4),
            "chunk_id": row[0],
            "source_file": row[1],
            "file_path": row[2],
            "doc_type": row[3],
            "title": row[4],
            "section_heading": row[5],
            "text": text[:500] + ("..." if len(text) > 500 else ""),
        })
    return results

# ---------------------------------------------------------------------------
# Pretty-print result
# ---------------------------------------------------------------------------

def print_result(result: dict, idx: int):
    print(f"  [{idx}] score={result['score']}")
    print(f"       source: {result['source_file']}")
    print(f"       type:   {result['doc_type']}")
    print(f"       heading: {result['section_heading']}")
    text = result['text']
    if len(text) > 250:
        text = text[:250] + "... [truncated]"
    print(f"       text:  {text}")
    print()

# ---------------------------------------------------------------------------
# Demo: run 3 canonical test queries
# ---------------------------------------------------------------------------

TEST_QUERIES = [
    {
        "label": "Factual single-hop",
        "query": "Какая БД используется в proshop_mern и почему именно она?",
        "top_k": 3,
        "expected": "adrs/adr-001-mongodb-vs-postgres.md",
    },
    {
        "label": "Multi-hop dependency",
        "query": "Какие фичи зависят от search_v2?",
        "top_k": 3,
        "expected": "feature-flags-spec.md, features/, dev-history.md",
    },
    {
        "label": "Filter by type + retrieval",
        "query": "Что случилось во время последнего incident с checkout?",
        "top_k": 3,
        "filter_type": "incident",
        "note": "No checkout-specific incident exists — will show best incident matches",
    },
]


def run_demo():
    print("=" * 72)
    print("M3-rag Semantic Search — Demo")
    print(f"Model: {MODEL}  |  DB: {DB_URL.split('@')[-1]}")
    print("=" * 72)

    for i, spec in enumerate(TEST_QUERIES, 1):
        label = spec["label"]
        query = spec["query"]
        top_k = spec["top_k"]
        expected = spec.get("expected", "")
        doc_type = spec.get("filter_type", None)
        source = spec.get("filter_source", None)
        note = spec.get("note", None)

        print(f"\n{'=' * 72}")
        print(f"Query #{i} — [{label}]")
        print(f"Q: {query}")
        if doc_type:
            print(f"  filter: doc_type='{doc_type}'")
        if source:
            print(f"  filter: source_file='{source}'")
        print(f"  expected from: {expected}")
        if note:
            print(f"  note: {note}")
        print(f"\nTop-{top_k} results:")
        print("-" * 72)

        results = search(query, top_k=top_k, doc_type=doc_type, source_file=source)

        if not results:
            print("  (no results)")
            continue

        for j, r in enumerate(results, 1):
            print_result(r, j)

# ---------------------------------------------------------------------------
# CLI: single query mode
# ---------------------------------------------------------------------------

def run_single(query: str, top_k: int, doc_type: str | None, source_file: str | None):
    results = search(query, top_k=top_k, doc_type=doc_type, source_file=source_file)
    if not results:
        print("(no results)")
        return
    for i, r in enumerate(results, 1):
        print_result(r, i)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Semantic search over RAG chunks")
    parser.add_argument("query", nargs="?", help="Search query (omit to run demo)")
    parser.add_argument("top_k", nargs="?", type=int, default=5, help="Number of results (default 5)")
    parser.add_argument("--type", dest="doc_type", default=None, help="Filter by doc_type (adr, incident, feature, ...)")
    parser.add_argument("--source", dest="source_file", default=None, help="Filter by source_file name")
    args = parser.parse_args()

    if args.query:
        run_single(args.query, args.top_k, args.doc_type, args.source_file)
    else:
        run_demo()

if __name__ == "__main__":
    main()
