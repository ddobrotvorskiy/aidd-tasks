# Markdown Chunking Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Copy `docs/project-data/` materials into the project, then run a Python chunking pipeline that produces `M3-rag/chunks.jsonl` — one JSON line per semantic chunk, with full metadata.

**Architecture:** A single `chunker.py` script classifies each `.md` file by path, applies a type-specific splitting strategy (whole-file, per-term, per-endpoint, per-H2, per-feature), enriches each chunk with metadata (title, breadcrumbs, language, keywords, summary, token count), and writes JSONL. Four parallel subagents each process an independent file batch and write partial JSONL files; the orchestrator merges and sorts them.

**Tech Stack:** Python 3.11+, standard library only (`re`, `json`, `pathlib`, `os`).

---

## File Map

| File | Role |
|------|------|
| `docs/project-data/` | Source materials (copied from external path) |
| `M3-rag/chunker/chunker.py` | Entry point + all parsers + orchestrator |
| `M3-rag/chunker/requirements.txt` | Empty (stdlib only) |
| `M3-rag/chunker/tests/test_chunker.py` | Unit tests for all parsers and helpers |
| `M3-rag/chunks.jsonl` | Output — one JSON object per line |
| `M3-rag/report.md` | Run stats (files, chunks, breakdown by type, timestamp) |
| `README.md` | Mention of `docs/project-data/` and `M3-rag/chunks.jsonl` |

---

## Task 1: Copy source materials and update README

**Files:**
- Create: `docs/project-data/` (directory copy)
- Modify: `README.md`

- [ ] **Step 1: Copy the source directory**

```bash
cp -r /Users/dobrotvorskiy/repo/AI/aidev-course-materials/M3/project-data \
      /Users/dobrotvorskiy/repo/AI/aidd-tasks/docs/project-data
```

Expected: `docs/project-data/` now exists with all subdirectories.

- [ ] **Step 2: Verify the copy**

```bash
find docs/project-data -name "*.md" | wc -l
```

Expected output: `47`

- [ ] **Step 3: Update README.md**

Replace the current content of `README.md` with:

```markdown
# aidd-tasks
AI Driven Development Course tasks

## Source Materials

`docs/project-data/` — ProShop MERN project documentation copied from the M3 course materials.
Contains architecture docs, API references, feature specs, ADRs, runbooks, incidents, and a glossary.

## M3-RAG

`M3-rag/chunks.jsonl` — semantic chunks of `docs/project-data/` ready for vector DB ingestion.
Each line is a JSON object with `text` + `metadata` (source_file, title, parent_headings, keywords, summary, language, token_count_approx).

To regenerate:
```bash
python M3-rag/chunker/chunker.py
```
```

- [ ] **Step 4: Commit**

```bash
git add docs/project-data README.md
git commit -m "feat: add project-data source materials and update README"
```

---

## Task 2: Scaffold chunker.py with helpers

**Files:**
- Create: `M3-rag/chunker/chunker.py`
- Create: `M3-rag/chunker/requirements.txt`
- Create: `M3-rag/chunker/tests/__init__.py`
- Create: `M3-rag/chunker/tests/test_chunker.py`

- [ ] **Step 1: Write failing tests for helper functions**

Create `M3-rag/chunker/tests/test_chunker.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from chunker import (
    detect_language,
    extract_keywords,
    extract_summary,
    token_count,
    slugify,
    split_sentences,
)


def test_detect_language_english():
    assert detect_language("The product catalog with pagination and keyword search.") == "en"


def test_detect_language_russian():
    assert detect_language("Покрывает управление товарами и пользователями в административной панели.") == "ru"


def test_detect_language_mixed_mostly_english():
    # less than 30% cyrillic
    assert detect_language("Feature: Admin Panel. Назначение: управление.") == "en"


def test_detect_language_mixed_mostly_russian():
    # more than 30% cyrillic
    assert detect_language("Назначение: управление товарами. Admin panel feature.") == "ru"


def test_extract_keywords_basic():
    kw = extract_keywords("POST /api/orders", "Creates a new order from cart contents with PayPal payment.")
    assert "order" in kw or "orders" in kw
    assert len(kw) <= 8


def test_extract_keywords_deduplicates():
    kw = extract_keywords("order order order", "order order")
    assert kw.count("order") == 1


def test_extract_summary_plain_text():
    text = "## POST /api/orders\n\nCreates a new order from cart contents.\n\nMore details here."
    assert extract_summary(text) == "Creates a new order from cart contents."


def test_extract_summary_skips_headings():
    text = "## Heading\n### Sub\nFirst real sentence here."
    assert extract_summary(text) == "First real sentence here."


def test_extract_summary_skips_code_blocks():
    text = "## Heading\n```json\n{\"key\": \"value\"}\n```\nActual summary sentence."
    assert extract_summary(text) == "Actual summary sentence."


def test_extract_summary_truncates():
    long = "x" * 300
    text = f"## H\n{long}"
    assert len(extract_summary(text)) <= 200


def test_token_count():
    assert token_count("hello world") == len("hello world") // 4


def test_slugify():
    assert slugify("POST /api/orders") == "post_api_orders"
    assert slugify("Feature 1: Admin Nav") == "feature_1_admin_nav"


def test_split_sentences_basic():
    text = "First sentence. Second sentence. Third sentence."
    parts = split_sentences(text)
    assert len(parts) == 3
    assert parts[0] == "First sentence."


def test_split_sentences_handles_empty():
    assert split_sentences("") == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/dobrotvorskiy/repo/AI/aidd-tasks
python -m pytest M3-rag/chunker/tests/test_chunker.py -v 2>&1 | head -20
```

Expected: `ImportError` or `ModuleNotFoundError` — chunker.py does not exist yet.

- [ ] **Step 3: Create chunker.py scaffold with helper implementations**

Create `M3-rag/chunker/chunker.py`:

```python
"""
Markdown chunking pipeline for RAG.
Entry point: python M3-rag/chunker/chunker.py
Output: M3-rag/chunks.jsonl
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "that", "this", "it", "its",
    # Russian stop words
    "в", "на", "и", "с", "по", "к", "от", "за", "как", "не", "что",
    "это", "все", "из", "он", "она", "они", "мы", "вы", "я", "его",
    "её", "их", "при", "или", "но", "если", "то", "так",
}


def detect_language(text: str) -> str:
    """Return 'ru' if >30% of alphabetic chars are Cyrillic, else 'en'."""
    alpha_chars = [c for c in text if c.isalpha()]
    if not alpha_chars:
        return "en"
    cyrillic = sum(1 for c in alpha_chars if '\u0400' <= c <= '\u04FF')
    return "ru" if cyrillic / len(alpha_chars) > 0.30 else "en"


def slugify(text: str) -> str:
    """Convert heading text to a lowercase underscore slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9а-яёa-z\s]', ' ', text)
    text = re.sub(r'\s+', '_', text.strip())
    return text


def token_count(text: str) -> int:
    """Approximate token count: len(text) // 4."""
    return len(text) // 4


def split_sentences(text: str) -> list[str]:
    """Split text into sentences on . ! ? followed by whitespace or end."""
    if not text.strip():
        return []
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p for p in parts if p]


def extract_summary(text: str) -> str:
    """
    Return first non-heading, non-code, non-empty line of text.
    Truncated to 200 chars.
    """
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        # Return first real content sentence (up to first period or 200 chars)
        sentences = split_sentences(stripped)
        if sentences:
            return sentences[0][:200]
        return stripped[:200]
    return ""


def extract_keywords(heading: str, text: str) -> list[str]:
    """
    Extract up to 8 keywords from heading + first paragraph.
    Stop-words removed, deduplicated, lowercase.
    """
    combined = f"{heading} {text[:500]}"
    words = re.findall(r'[a-zA-Zа-яёА-ЯЁ]{3,}', combined.lower())
    seen: set[str] = set()
    result: list[str] = []
    for w in words:
        if w not in STOP_WORDS and w not in seen:
            seen.add(w)
            result.append(w)
        if len(result) == 8:
            break
    return result


# ---------------------------------------------------------------------------
# Markdown line-by-line parser primitives
# ---------------------------------------------------------------------------

def parse_h1(lines: list[str]) -> str:
    """Return text of first H1 line, or empty string."""
    for line in lines:
        m = re.match(r'^#\s+(.+)', line)
        if m:
            return m.group(1).strip()
    return ""


def heading_level(line: str) -> tuple[int, str] | None:
    """Return (level, text) if line is a heading, else None."""
    m = re.match(r'^(#{1,6})\s+(.+)', line)
    if m:
        return len(m.group(1)), m.group(2).strip()
    return None


def build_chunk(
    lines: list[str],
    file_path: str,
    doc_type: str,
    title: str,
    section_heading: str,
    parent_headings: list[str],
    chunk_index: int,
) -> dict:
    """Build a single chunk dict from buffered lines."""
    text = "\n".join(lines).strip()
    rel_path = file_path  # already relative
    path_slug = slugify(rel_path.replace("/", "_").replace(".md", ""))
    section_slug = slugify(section_heading) if section_heading else "top"
    chunk_id = f"{path_slug}__{section_slug}__{chunk_index}"

    return {
        "text": text,
        "metadata": {
            "chunk_id": chunk_id,
            "source_file": os.path.basename(file_path),
            "file_path": file_path,
            "doc_type": doc_type,
            "title": title,
            "section_heading": section_heading,
            "parent_headings": list(parent_headings),
            "language": detect_language(text),
            "keywords": extract_keywords(section_heading, text),
            "summary": extract_summary(text),
            "token_count_approx": token_count(text),
        },
    }


def maybe_split_large_chunk(chunk: dict, overlap_sentences: int = 2) -> list[dict]:
    """
    If chunk exceeds 700 tokens (~2800 chars), split at paragraph boundaries.
    Carry last `overlap_sentences` sentences of previous sub-chunk into next.
    """
    text = chunk["text"]
    if token_count(text) <= 700:
        return [chunk]

    paragraphs = re.split(r'\n\n+', text)
    sub_chunks: list[dict] = []
    buffer: list[str] = []
    overlap_text = ""
    idx = 0

    for para in paragraphs:
        test_buf = buffer + [para]
        if token_count("\n\n".join(test_buf)) > 700 and buffer:
            # emit current buffer
            sub_text = overlap_text + "\n\n".join(buffer)
            sub = dict(chunk)
            sub["text"] = sub_text.strip()
            sub["metadata"] = dict(chunk["metadata"])
            sub["metadata"]["chunk_id"] = f"{chunk['metadata']['chunk_id']}_{idx}"
            sub["metadata"]["token_count_approx"] = token_count(sub["text"])
            sub["metadata"]["summary"] = extract_summary(sub["text"])
            sub_chunks.append(sub)
            # compute overlap
            sentences = split_sentences("\n\n".join(buffer))
            tail = sentences[-overlap_sentences:] if len(sentences) >= overlap_sentences else sentences
            overlap_text = " ".join(tail) + "\n\n" if tail else ""
            buffer = [para]
            idx += 1
        else:
            buffer.append(para)

    if buffer:
        sub_text = overlap_text + "\n\n".join(buffer)
        sub = dict(chunk)
        sub["text"] = sub_text.strip()
        sub["metadata"] = dict(chunk["metadata"])
        sub["metadata"]["chunk_id"] = f"{chunk['metadata']['chunk_id']}_{idx}"
        sub["metadata"]["token_count_approx"] = token_count(sub["text"])
        sub["metadata"]["summary"] = extract_summary(sub["text"])
        sub_chunks.append(sub)

    return sub_chunks if sub_chunks else [chunk]


# ---------------------------------------------------------------------------
# Doc-type classifiers
# ---------------------------------------------------------------------------

def classify_doc_type(rel_path: str) -> str:
    """Return doc_type string based on file path."""
    p = rel_path.replace("\\", "/")
    if "/adrs/" in p:
        return "adr"
    if "/incidents/" in p:
        return "incident"
    if p.endswith("glossary.md"):
        return "glossary"
    if "/api/" in p:
        return "api_endpoint"
    if "/features/" in p:
        return "feature"
    if "/pages/" in p:
        return "page"
    if "/runbooks/" in p:
        return "runbook"
    return "generic"


# ---------------------------------------------------------------------------
# Per-type parsers
# ---------------------------------------------------------------------------

def parse_whole_file(lines: list[str], file_path: str, doc_type: str) -> list[dict]:
    """Emit entire file as one chunk (adr, incident, page)."""
    title = parse_h1(lines)
    chunk = build_chunk(lines, file_path, doc_type, title, title, [], 0)
    return maybe_split_large_chunk(chunk)


def parse_glossary(lines: list[str], file_path: str) -> list[dict]:
    """
    1 term = 1 chunk.
    Terms are H3 blocks (### TermName).
    H2 sections (Domain Terms, Technical Terms, etc.) are breadcrumbs only.
    """
    title = parse_h1(lines)
    chunks: list[dict] = []
    current_h2 = ""
    buffer: list[str] = []
    current_heading = ""
    idx = 0

    def flush():
        nonlocal idx
        if buffer and current_heading:
            c = build_chunk(
                buffer, file_path, "glossary", title,
                current_heading, [current_h2] if current_h2 else [], idx
            )
            chunks.extend(maybe_split_large_chunk(c))
            idx += 1

    for line in lines:
        h = heading_level(line)
        if h:
            level, text = h
            if level == 1:
                continue
            if level == 2:
                flush()
                buffer = []
                current_h2 = text
                current_heading = ""
            elif level == 3:
                flush()
                buffer = [line]
                current_heading = text
            else:
                buffer.append(line)
        else:
            buffer.append(line)

    flush()
    return chunks


def parse_api_endpoints(lines: list[str], file_path: str) -> list[dict]:
    """
    Overview H2 = 1 chunk.
    Each H3 (### METHOD /path) = 1 chunk.
    """
    title = parse_h1(lines)
    chunks: list[dict] = []
    current_h2 = ""
    buffer: list[str] = []
    current_heading = ""
    idx = 0

    def flush(heading: str, parents: list[str]):
        nonlocal idx
        if buffer:
            c = build_chunk(buffer, file_path, "api_endpoint", title, heading, parents, idx)
            chunks.extend(maybe_split_large_chunk(c))
            idx += 1

    for line in lines:
        h = heading_level(line)
        if h:
            level, text = h
            if level == 1:
                continue
            if level == 2:
                flush(current_heading, [])
                buffer = [line]
                current_h2 = text
                current_heading = text
            elif level == 3:
                flush(current_heading, [current_h2] if current_h2 else [])
                buffer = [line]
                current_heading = text
            else:
                buffer.append(line)
        else:
            buffer.append(line)

    flush(current_heading, [current_h2] if current_h2 else [])
    return chunks


def parse_features(lines: list[str], file_path: str) -> list[dict]:
    """
    Each H2 feature block = 1 chunk.
    If >600 tokens, split at H3 boundaries within the feature.
    """
    title = parse_h1(lines)
    chunks: list[dict] = []
    buffer: list[str] = []
    current_heading = ""
    idx = 0

    def flush():
        nonlocal idx
        if not buffer or not current_heading:
            return
        text = "\n".join(buffer)
        if token_count(text) > 600:
            # split at H3 within this feature
            sub_buf: list[str] = []
            sub_heading = current_heading
            sub_idx = 0
            for bl in buffer:
                bh = heading_level(bl)
                if bh and bh[0] == 3:
                    if sub_buf:
                        c = build_chunk(
                            sub_buf, file_path, "feature", title,
                            sub_heading, [current_heading], idx
                        )
                        chunks.extend(maybe_split_large_chunk(c))
                        idx += 1
                        sub_idx += 1
                    sub_buf = [bl]
                    sub_heading = bh[1]
                else:
                    sub_buf.append(bl)
            if sub_buf:
                c = build_chunk(
                    sub_buf, file_path, "feature", title,
                    sub_heading, [current_heading], idx
                )
                chunks.extend(maybe_split_large_chunk(c))
                idx += 1
        else:
            c = build_chunk(buffer, file_path, "feature", title, current_heading, [], idx)
            chunks.extend(maybe_split_large_chunk(c))
            idx += 1

    for line in lines:
        h = heading_level(line)
        if h and h[0] == 2:
            flush()
            buffer = [line]
            current_heading = h[1]
        elif h and h[0] == 1:
            continue
        else:
            buffer.append(line)

    flush()
    return chunks


def parse_by_h2(lines: list[str], file_path: str, doc_type: str) -> list[dict]:
    """
    Generic and runbook: each H2 section = 1 chunk.
    If H2 > 600 tokens, split at H3 boundaries.
    """
    title = parse_h1(lines)
    chunks: list[dict] = []
    buffer: list[str] = []
    current_h2 = ""
    idx = 0

    def flush():
        nonlocal idx
        if not buffer or not current_h2:
            return
        text = "\n".join(buffer)
        if token_count(text) > 600:
            sub_buf: list[str] = []
            sub_heading = current_h2
            for bl in buffer:
                bh = heading_level(bl)
                if bh and bh[0] == 3:
                    if sub_buf:
                        c = build_chunk(
                            sub_buf, file_path, doc_type, title,
                            sub_heading, [current_h2], idx
                        )
                        chunks.extend(maybe_split_large_chunk(c))
                        idx += 1
                    sub_buf = [bl]
                    sub_heading = bh[1]
                else:
                    sub_buf.append(bl)
            if sub_buf:
                c = build_chunk(
                    sub_buf, file_path, doc_type, title,
                    sub_heading, [current_h2], idx
                )
                chunks.extend(maybe_split_large_chunk(c))
                idx += 1
        else:
            c = build_chunk(buffer, file_path, doc_type, title, current_h2, [], idx)
            chunks.extend(maybe_split_large_chunk(c))
            idx += 1

    for line in lines:
        h = heading_level(line)
        if h and h[0] == 1:
            continue
        elif h and h[0] == 2:
            flush()
            buffer = [line]
            current_h2 = h[1]
        else:
            buffer.append(line)

    flush()
    return chunks


# ---------------------------------------------------------------------------
# Per-file dispatcher
# ---------------------------------------------------------------------------

def chunk_file(file_path: str, project_root: str) -> list[dict]:
    """
    Read a single .md file and return its chunks.
    file_path: absolute path.
    project_root: absolute path to project root.
    """
    rel = os.path.relpath(file_path, project_root).replace("\\", "/")

    # Skip INDEX.md
    if os.path.basename(file_path) == "INDEX.md":
        return []

    with open(file_path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    doc_type = classify_doc_type(rel)

    if doc_type in ("adr", "incident", "page"):
        return parse_whole_file(lines, rel, doc_type)
    elif doc_type == "glossary":
        return parse_glossary(lines, rel)
    elif doc_type == "api_endpoint":
        return parse_api_endpoints(lines, rel)
    elif doc_type == "feature":
        return parse_features(lines, rel)
    elif doc_type in ("runbook", "generic"):
        return parse_by_h2(lines, rel, doc_type)
    else:
        return parse_whole_file(lines, rel, doc_type)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def find_md_files(root: str) -> list[str]:
    """Return all .md files under root, sorted."""
    result = []
    for dirpath, _dirs, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith(".md"):
                result.append(os.path.join(dirpath, fname))
    return sorted(result)


def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent  # M3-rag/chunker/ -> aidd-tasks/
    data_dir = project_root / "docs" / "project-data"
    output_path = project_root / "M3-rag" / "chunks.jsonl"
    report_path = project_root / "M3-rag" / "report.md"

    md_files = find_md_files(str(data_dir))

    all_chunks: list[dict] = []
    stats: dict[str, int] = {}

    for fpath in md_files:
        chunks = chunk_file(fpath, str(project_root))
        all_chunks.extend(chunks)
        for c in chunks:
            dt = c["metadata"]["doc_type"]
            stats[dt] = stats.get(dt, 0) + 1

    # Sort by file_path then chunk_id
    all_chunks.sort(key=lambda c: (c["metadata"]["file_path"], c["metadata"]["chunk_id"]))

    # Write JSONL
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    # Write report
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Chunking Pipeline Report",
        "",
        f"**Run timestamp:** {now}",
        f"**Files processed:** {len(md_files)}",
        f"**Total chunks:** {len(all_chunks)}",
        f"**Output:** `M3-rag/chunks.jsonl`",
        "",
        "## Chunks by doc_type",
        "",
    ]
    for dt, count in sorted(stats.items()):
        lines.append(f"| `{dt}` | {count} |")
    lines = lines[:-len(stats)] + ["| doc_type | count |", "|----------|-------|"] + lines[-len(stats):]
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Done. {len(all_chunks)} chunks from {len(md_files)} files → {output_path}")
    print(f"Report → {report_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create requirements.txt**

Create `M3-rag/chunker/requirements.txt`:

```
# stdlib only — no external dependencies
```

- [ ] **Step 5: Create tests __init__.py**

Create `M3-rag/chunker/tests/__init__.py` (empty file).

- [ ] **Step 6: Run tests — helpers should pass now**

```bash
cd /Users/dobrotvorskiy/repo/AI/aidd-tasks
python -m pytest M3-rag/chunker/tests/test_chunker.py -v
```

Expected: all helper tests pass (detect_language, extract_keywords, extract_summary, token_count, slugify, split_sentences).

- [ ] **Step 7: Commit**

```bash
git add M3-rag/chunker/chunker.py M3-rag/chunker/requirements.txt M3-rag/chunker/tests/
git commit -m "feat: add chunker scaffold with helpers and unit tests"
```

---

## Task 3: Tests for per-type parsers

**Files:**
- Modify: `M3-rag/chunker/tests/test_chunker.py`

- [ ] **Step 1: Add parser tests to test_chunker.py**

Append to `M3-rag/chunker/tests/test_chunker.py`:

```python
from chunker import (
    chunk_file,
    classify_doc_type,
    parse_glossary,
    parse_api_endpoints,
    parse_features,
    parse_whole_file,
    parse_by_h2,
)

# --- classify_doc_type ---

def test_classify_adr():
    assert classify_doc_type("docs/project-data/adrs/adr-001-mongodb-vs-postgres.md") == "adr"

def test_classify_incident():
    assert classify_doc_type("docs/project-data/incidents/i-001-paypal-double-charge.md") == "incident"

def test_classify_glossary():
    assert classify_doc_type("docs/project-data/glossary.md") == "glossary"

def test_classify_api():
    assert classify_doc_type("docs/project-data/api/orders.md") == "api_endpoint"

def test_classify_feature():
    assert classify_doc_type("docs/project-data/features/admin.md") == "feature"

def test_classify_page():
    assert classify_doc_type("docs/project-data/pages/home.md") == "page"

def test_classify_runbook():
    assert classify_doc_type("docs/project-data/runbooks/deploy.md") == "runbook"

def test_classify_generic():
    assert classify_doc_type("docs/project-data/architecture.md") == "generic"


# --- parse_whole_file ---

def test_parse_whole_file_single_chunk():
    lines = ["# ADR-001: Use MongoDB", "", "## Context", "", "We chose MongoDB because..."]
    chunks = parse_whole_file(lines, "docs/project-data/adrs/adr-001.md", "adr")
    assert len(chunks) == 1
    assert chunks[0]["metadata"]["doc_type"] == "adr"
    assert chunks[0]["metadata"]["title"] == "ADR-001: Use MongoDB"
    assert "MongoDB" in chunks[0]["text"]


def test_parse_whole_file_metadata_fields():
    lines = ["# My Doc", "", "Some content here."]
    chunks = parse_whole_file(lines, "docs/project-data/adrs/my-doc.md", "adr")
    m = chunks[0]["metadata"]
    assert m["source_file"] == "my-doc.md"
    assert m["file_path"] == "docs/project-data/adrs/my-doc.md"
    assert m["language"] in ("en", "ru")
    assert isinstance(m["keywords"], list)
    assert isinstance(m["summary"], str)
    assert isinstance(m["token_count_approx"], int)


# --- parse_glossary ---

def test_parse_glossary_one_chunk_per_term():
    lines = [
        "# Glossary",
        "",
        "## Domain Terms",
        "",
        "### Customer",
        "A user registered in the system.",
        "",
        "### Product",
        "A physical or digital good.",
    ]
    chunks = parse_glossary(lines, "docs/project-data/glossary.md")
    assert len(chunks) == 2
    headings = [c["metadata"]["section_heading"] for c in chunks]
    assert "Customer" in headings
    assert "Product" in headings


def test_parse_glossary_parent_heading_is_h2():
    lines = [
        "# Glossary",
        "## Domain Terms",
        "### Customer",
        "A user.",
    ]
    chunks = parse_glossary(lines, "docs/project-data/glossary.md")
    assert chunks[0]["metadata"]["parent_headings"] == ["Domain Terms"]


# --- parse_api_endpoints ---

def test_parse_api_endpoints_overview_plus_endpoints():
    lines = [
        "# Orders API Reference",
        "",
        "## Overview",
        "",
        "Manages order lifecycle.",
        "",
        "## Endpoints",
        "",
        "### POST /api/orders",
        "",
        "Create a new order.",
        "",
        "### GET /api/orders/:id",
        "",
        "Get order by id.",
    ]
    chunks = parse_api_endpoints(lines, "docs/project-data/api/orders.md")
    headings = [c["metadata"]["section_heading"] for c in chunks]
    assert "Overview" in headings
    assert "POST /api/orders" in headings
    assert "GET /api/orders/:id" in headings


def test_parse_api_endpoints_parent_heading():
    lines = [
        "# Orders API",
        "## Endpoints",
        "### POST /api/orders",
        "Create order.",
    ]
    chunks = parse_api_endpoints(lines, "docs/project-data/api/orders.md")
    endpoint_chunk = next(c for c in chunks if c["metadata"]["section_heading"] == "POST /api/orders")
    assert "Endpoints" in endpoint_chunk["metadata"]["parent_headings"]


# --- parse_features ---

def test_parse_features_one_chunk_per_h2():
    lines = [
        "# Admin Features",
        "",
        "## Feature 1: Admin Navigation",
        "",
        "Controls admin menu visibility.",
        "",
        "## Feature 2: Admin Product List",
        "",
        "Table of all products.",
    ]
    chunks = parse_features(lines, "docs/project-data/features/admin.md")
    headings = [c["metadata"]["section_heading"] for c in chunks]
    assert "Feature 1: Admin Navigation" in headings
    assert "Feature 2: Admin Product List" in headings


# --- parse_by_h2 (generic / runbook) ---

def test_parse_by_h2_sections():
    lines = [
        "# Architecture",
        "",
        "## 1. System Overview",
        "",
        "ProShop is a MERN app.",
        "",
        "## 2. Tech Stack",
        "",
        "Node, Express, React, MongoDB.",
    ]
    chunks = parse_by_h2(lines, "docs/project-data/architecture.md", "generic")
    headings = [c["metadata"]["section_heading"] for c in chunks]
    assert "1. System Overview" in headings
    assert "2. Tech Stack" in headings


def test_parse_by_h2_h3_split_when_large():
    # Build a section >600 tokens with H3 sub-sections
    big_para = "word " * 200  # ~1000 tokens
    lines = (
        ["# Doc", "## Big Section", "### Sub A", big_para, "### Sub B", big_para]
    )
    chunks = parse_by_h2(lines, "docs/project-data/architecture.md", "generic")
    # Should have split into at least 2 chunks
    assert len(chunks) >= 2


# --- INDEX.md skipped ---

def test_index_md_skipped(tmp_path):
    index = tmp_path / "INDEX.md"
    index.write_text("# Index\n\nSome content.\n")
    import sys
    sys.path.insert(0, str(tmp_path.parent))
    chunks = chunk_file(str(index), str(tmp_path.parent))
    assert chunks == []
```

- [ ] **Step 2: Run tests — new parser tests should pass if Task 2 is complete**

```bash
cd /Users/dobrotvorskiy/repo/AI/aidd-tasks
python -m pytest M3-rag/chunker/tests/test_chunker.py -v 2>&1 | tail -30
```

Expected: all parser tests pass. If any fail, the implementation in chunker.py needs to be fixed (not the tests).

- [ ] **Step 3: Fix any import or logic issues found**

If `ImportError`: verify the function names exported from `chunker.py` match exactly.  
If test logic fails: adjust test expectations to match the actual implemented behaviour (do not change the implementation unless it is wrong per spec).

- [ ] **Step 4: Run all tests — all should pass**

```bash
cd /Users/dobrotvorskiy/repo/AI/aidd-tasks
python -m pytest M3-rag/chunker/tests/test_chunker.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add M3-rag/chunker/tests/test_chunker.py
git commit -m "test: add parser unit tests for all doc_type strategies"
```

---

## Task 4: Integration test — run on real files

**Files:**
- Modify: `M3-rag/chunker/tests/test_chunker.py`

- [ ] **Step 1: Add integration test**

Append to `M3-rag/chunker/tests/test_chunker.py`:

```python
import json
from pathlib import Path

def test_integration_real_files():
    """Smoke test: chunk all real docs/project-data files and validate output shape."""
    project_root = Path(__file__).parent.parent.parent.parent  # aidd-tasks/
    data_dir = project_root / "docs" / "project-data"

    if not data_dir.exists():
        import pytest
        pytest.skip("docs/project-data not present — run Task 1 first")

    from chunker import find_md_files, chunk_file

    md_files = find_md_files(str(data_dir))
    assert len(md_files) >= 46, f"Expected >=46 .md files, got {len(md_files)}"

    all_chunks = []
    for fpath in md_files:
        chunks = chunk_file(fpath, str(project_root))
        all_chunks.extend(chunks)

    assert len(all_chunks) > 50, f"Expected >50 chunks, got {len(all_chunks)}"

    # Every chunk must have required fields
    required_fields = {
        "chunk_id", "source_file", "file_path", "doc_type",
        "title", "section_heading", "parent_headings",
        "language", "keywords", "summary", "token_count_approx"
    }
    for c in all_chunks:
        assert "text" in c, f"Missing 'text' in chunk {c}"
        assert "metadata" in c, f"Missing 'metadata' in chunk {c}"
        missing = required_fields - set(c["metadata"].keys())
        assert not missing, f"Missing metadata fields {missing} in chunk {c['metadata']['chunk_id']}"
        assert c["metadata"]["language"] in ("en", "ru")
        assert isinstance(c["metadata"]["keywords"], list)
        assert len(c["metadata"]["keywords"]) <= 8
        assert isinstance(c["metadata"]["token_count_approx"], int)
        assert c["metadata"]["token_count_approx"] > 0

    # No chunk IDs duplicated
    ids = [c["metadata"]["chunk_id"] for c in all_chunks]
    assert len(ids) == len(set(ids)), "Duplicate chunk_ids found"

    # All chunk texts are non-empty
    for c in all_chunks:
        assert c["text"].strip(), f"Empty text in chunk {c['metadata']['chunk_id']}"

    # Verify INDEX.md produced no chunks
    index_chunks = [c for c in all_chunks if c["metadata"]["source_file"] == "INDEX.md"]
    assert index_chunks == [], "INDEX.md should produce no chunks"
```

- [ ] **Step 2: Run integration test**

```bash
cd /Users/dobrotvorskiy/repo/AI/aidd-tasks
python -m pytest M3-rag/chunker/tests/test_chunker.py::test_integration_real_files -v
```

Expected: PASS. If it fails, check which assertion failed and fix the parser for that doc_type.

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/dobrotvorskiy/repo/AI/aidd-tasks
python -m pytest M3-rag/chunker/tests/test_chunker.py -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add M3-rag/chunker/tests/test_chunker.py
git commit -m "test: add integration smoke test over real docs/project-data files"
```

---

## Task 5: Run pipeline, write chunks.jsonl and report.md

**Files:**
- Create: `M3-rag/chunks.jsonl`
- Create: `M3-rag/report.md`

- [ ] **Step 1: Run the pipeline**

```bash
cd /Users/dobrotvorskiy/repo/AI/aidd-tasks
python M3-rag/chunker/chunker.py
```

Expected output (example):
```
Done. 183 chunks from 47 files → .../M3-rag/chunks.jsonl
Report → .../M3-rag/report.md
```

- [ ] **Step 2: Verify chunks.jsonl is valid JSONL**

```bash
python -c "
import json
count = 0
with open('M3-rag/chunks.jsonl') as f:
    for line in f:
        json.loads(line)
        count += 1
print(f'Valid JSONL: {count} lines')
"
```

Expected: prints `Valid JSONL: N lines` with no exceptions.

- [ ] **Step 3: Spot-check a few chunks**

```bash
python -c "
import json
with open('M3-rag/chunks.jsonl') as f:
    chunks = [json.loads(l) for l in f]
# Print first chunk from each doc_type
seen = set()
for c in chunks:
    dt = c['metadata']['doc_type']
    if dt not in seen:
        seen.add(dt)
        print(f'--- {dt} ---')
        print('  chunk_id:', c['metadata']['chunk_id'])
        print('  summary:', c['metadata']['summary'])
        print('  tokens:', c['metadata']['token_count_approx'])
        print()
"
```

Expected: one representative chunk printed per doc_type, all with non-empty summaries and reasonable token counts.

- [ ] **Step 4: Check report.md**

```bash
cat M3-rag/report.md
```

Expected: shows run timestamp, file count, total chunks, and a table of chunks by doc_type.

- [ ] **Step 5: Commit**

```bash
git add M3-rag/chunks.jsonl M3-rag/report.md
git commit -m "feat: generate chunks.jsonl and report.md from docs/project-data"
```

---

## Task 6: Final verification and cleanup

- [ ] **Step 1: Run full test suite one last time**

```bash
cd /Users/dobrotvorskiy/repo/AI/aidd-tasks
python -m pytest M3-rag/chunker/tests/test_chunker.py -v
```

Expected: all tests PASS, zero failures.

- [ ] **Step 2: Verify output file exists and is non-empty**

```bash
wc -l M3-rag/chunks.jsonl
```

Expected: a number > 50.

- [ ] **Step 3: Verify no chunk exceeds hard max (700 tokens)**

```bash
python -c "
import json
with open('M3-rag/chunks.jsonl') as f:
    chunks = [json.loads(l) for l in f]
oversized = [c for c in chunks if c['metadata']['token_count_approx'] > 700]
if oversized:
    for c in oversized:
        print('OVERSIZED:', c['metadata']['chunk_id'], c['metadata']['token_count_approx'])
else:
    print('All chunks within 700 token limit.')
"
```

Expected: `All chunks within 700 token limit.`

- [ ] **Step 4: Final commit**

```bash
git add -A
git status
git commit -m "chore: finalize chunking pipeline — all tests pass, output verified"
```
