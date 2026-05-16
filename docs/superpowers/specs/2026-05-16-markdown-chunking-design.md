# Design: Markdown Chunking Pipeline for RAG

**Date:** 2026-05-16  
**Status:** Approved  
**Scope:** M3-rag task — split `docs/project-data/` markdown files into chunks for a vector database

---

## 1. Goal

Produce a file `M3-rag/chunks.jsonl` where every line is a JSON object with `text` + `metadata`. The chunks are semantically coherent, sized for a vector embedding model (300–600 tokens target), and carry enough metadata for retrieval filtering and citation.

Source: 47 `.md` files copied to `docs/project-data/` from the course materials.  
Excluded: `features.json` (not markdown), `pages/INDEX.md` (index only, no content).

---

## 2. Project Structure

```
aidd-tasks/
├── docs/
│   └── project-data/          ← source materials (copied from M3/project-data)
│       ├── adrs/
│       ├── api/
│       ├── features/
│       ├── pages/
│       ├── incidents/
│       ├── runbooks/
│       ├── architecture.md
│       ├── best-practices.md
│       ├── dev-history.md
│       ├── feature-flags-spec.md
│       ├── features-analysis-ru.md
│       └── glossary.md
├── M3-rag/
│   ├── chunker/
│   │   ├── chunker.py         ← orchestrator + all parsers
│   │   └── requirements.txt
│   ├── chunks.jsonl           ← output
│   └── report.md              ← describes what was done, chunk stats, output path
└── README.md                  ← mentions docs/project-data as source materials
```

---

## 3. Document Types and Chunking Strategy

Each file is classified by its path. Classification is deterministic — no heuristics needed.

| Type | Path pattern | Chunking rule |
|------|-------------|---------------|
| `adr` | `adrs/*.md` | Whole file = 1 chunk (66–109 lines, fits in 300–500 tokens) |
| `glossary` | `glossary.md` | 1 term (H3 block + its body) = 1 chunk |
| `api_endpoint` | `api/*.md` | Overview H2 = 1 chunk; each H3 endpoint (`### METHOD /path`) = 1 chunk |
| `feature` | `features/*.md` | Each H2 feature block = 1 chunk; if >600 tokens, split at H3 boundaries within the feature |
| `page` | `pages/*.md` (not INDEX) | Whole file = 1 chunk (~40 lines, compact) |
| `incident` | `incidents/*.md` | Whole file = 1 chunk (~120 lines) |
| `runbook` | `runbooks/*.md` | Each H2 section = 1 chunk |
| `generic` | everything else (architecture, best-practices, feature-flags-spec, dev-history, features-analysis-ru) | Each H2 section = 1 chunk; if H2 > 600 tokens, split at H3 boundaries |

`pages/INDEX.md` is explicitly skipped.

---

## 4. Chunk Size and Overlap

**Target size:** 300–600 tokens. Approximation: `len(text) // 4` characters.

**Hard max:** 700 tokens (~2800 chars). If a section exceeds this after H3 splitting, split at paragraph boundaries (double newline), carrying the last 2 sentences into the next chunk as overlap.

**Overlap rule:** Overlap is applied **only** when cutting continuous prose mid-section (paragraph split). It is **not** applied between natural structural boundaries (endpoint-to-endpoint, feature-to-feature, term-to-term). Overlap size: last 2 sentences of previous chunk prepended to next.

---

## 5. Chunk Schema

Each line in `chunks.jsonl`:

```json
{
  "text": "...",
  "metadata": {
    "chunk_id": "api/orders__endpoint_post_api_orders__0",
    "source_file": "orders.md",
    "file_path": "docs/project-data/api/orders.md",
    "doc_type": "api_endpoint",
    "title": "Orders API Reference",
    "section_heading": "POST /api/orders",
    "parent_headings": ["Endpoints"],
    "language": "en",
    "keywords": ["order", "create", "POST", "PayPal", "cart"],
    "summary": "Creates a new order from cart contents with shipping info and returns the saved order document.",
    "token_count_approx": 380
  }
}
```

**Field rules:**

| Field | Source | Notes |
|-------|--------|-------|
| `chunk_id` | `{relative_path_slug}__{section_slug}__{index}` | Unique, stable, human-readable |
| `source_file` | `os.path.basename(file_path)` | |
| `file_path` | Path relative to project root | e.g. `docs/project-data/api/orders.md` |
| `doc_type` | Classifier (section 3) | |
| `title` | H1 of the file | Falls back to filename stem if no H1 |
| `section_heading` | Nearest heading that opened this chunk | H2 or H3 |
| `parent_headings` | List of ancestor headings above `section_heading` | Breadcrumb; empty list for top-level |
| `language` | Auto-detected | If >30% of alphabetic characters are Cyrillic → `"ru"`, else `"en"` |
| `keywords` | Extracted from section headings + first paragraph | Stop-words removed; max 8 items |
| `summary` | First non-heading, non-code, non-empty line of chunk text | Truncated to 200 chars |
| `token_count_approx` | `len(text) // 4` | Integer |

---

## 6. Parallel Subagent Split

4 subagents process independent file batches concurrently. Each returns a list of chunk dicts. The orchestrator merges them and writes `chunks.jsonl` sorted by `file_path` then `chunk_id`.

| Subagent | Files | Count |
|----------|-------|-------|
| Agent 1 | `adrs/` (5) + `incidents/` (3) + `pages/` (14, excluding INDEX) | 22 files |
| Agent 2 | `api/` (5) + `features/` (6) | 11 files |
| Agent 3 | `runbooks/` (6) + `glossary.md` | 7 files |
| Agent 4 | `architecture.md` + `best-practices.md` + `feature-flags-spec.md` + `dev-history.md` + `features-analysis-ru.md` | 5 files |

---

## 7. Implementation

**Language:** Python 3.11+  
**Dependencies:** Standard library only (`re`, `os`, `json`, `pathlib`). No `mistune` or other markdown parsers — line-by-line parsing is sufficient given the well-structured input.

**Entry point:** `python M3-rag/chunker/chunker.py`

**Algorithm per file:**
1. Read file lines
2. Classify doc_type from path
3. Detect H1 (title)
4. Walk lines, tracking heading stack (H1/H2/H3)
5. At each structural boundary (per type's rule), emit buffered lines as a chunk
6. If buffered chunk exceeds 700 tokens, split at paragraph boundaries with 2-sentence overlap
7. For each chunk: detect language, extract keywords, extract summary, compute token count

**Output:** `M3-rag/chunks.jsonl` — one JSON object per line, UTF-8, no trailing newline issues.

**report.md** contains: total files processed, total chunks produced, chunk count by doc_type, output file path, and run timestamp.

---

## 8. What Is Not in Scope

- Embedding generation (out of scope for this task)
- Vector DB loading (out of scope)
- Incremental / watch-mode re-chunking
- Chunk deduplication
- Translation of Russian content to English
