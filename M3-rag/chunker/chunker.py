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
    text = re.sub(r'[^a-z0-9а-яёё\s]', ' ', text)
    text = re.sub(r'\s+', '_', text.strip())
    return text


def token_count(text: str) -> int:
    """Approximate token count: len(text) // 4."""
    return len(text) // 4


def split_sentences(text: str) -> list:
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


def extract_keywords(heading: str, text: str) -> list:
    """
    Extract up to 8 keywords from heading + first paragraph.
    Stop-words removed, deduplicated, lowercase.
    """
    combined = f"{heading} {text[:500]}"
    words = re.findall(r'[a-zA-Zа-яёА-ЯЁ]{3,}', combined.lower())
    seen = set()
    result = []
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

def parse_h1(lines: list) -> str:
    """Return text of first H1 line, or empty string."""
    for line in lines:
        m = re.match(r'^#\s+(.+)', line)
        if m:
            return m.group(1).strip()
    return ""


def heading_level(line: str):
    """Return (level, text) if line is a heading, else None."""
    m = re.match(r'^(#{1,6})\s+(.+)', line)
    if m:
        return len(m.group(1)), m.group(2).strip()
    return None


def build_chunk(
    lines: list,
    file_path: str,
    doc_type: str,
    title: str,
    section_heading: str,
    parent_headings: list,
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


def maybe_split_large_chunk(chunk: dict, overlap_sentences: int = 2) -> list:
    """
    If chunk exceeds 700 tokens (~2800 chars), split at paragraph boundaries.
    Carry last `overlap_sentences` sentences of previous sub-chunk into next.
    If a single paragraph exceeds 700 tokens, split at sentence boundaries.
    """
    text = chunk["text"]
    if token_count(text) <= 700:
        return [chunk]

    paragraphs = re.split(r'\n\n+', text)

    # If only one paragraph, split at sentence boundaries instead
    if len(paragraphs) == 1:
        sentences = split_sentences(text)
        if len(sentences) <= 1:
            # Cannot split further — return as-is (original chunk_id, no suffix)
            return [chunk]
        # Build sentence-level sub-chunks
        sub_chunks: list = []
        buffer_sents: list = []
        overlap_text = ""
        idx = 0
        for sent in sentences:
            test = " ".join(buffer_sents + [sent])
            if token_count(overlap_text + test) > 700 and buffer_sents:
                sub_text = (overlap_text + " ".join(buffer_sents)).strip()
                sub = dict(chunk)
                sub["text"] = sub_text
                sub["metadata"] = dict(chunk["metadata"])
                sub["metadata"]["chunk_id"] = f"{chunk['metadata']['chunk_id']}_{idx}"
                sub["metadata"]["token_count_approx"] = token_count(sub_text)
                sub["metadata"]["summary"] = extract_summary(sub_text)
                sub_chunks.append(sub)
                tail = buffer_sents[-overlap_sentences:] if len(buffer_sents) >= overlap_sentences else buffer_sents
                overlap_text = " ".join(tail) + " " if tail else ""
                buffer_sents = [sent]
                idx += 1
            else:
                buffer_sents.append(sent)
        if buffer_sents:
            sub_text = (overlap_text + " ".join(buffer_sents)).strip()
            sub = dict(chunk)
            sub["text"] = sub_text
            sub["metadata"] = dict(chunk["metadata"])
            sub["metadata"]["chunk_id"] = f"{chunk['metadata']['chunk_id']}_{idx}"
            sub["metadata"]["token_count_approx"] = token_count(sub_text)
            sub["metadata"]["summary"] = extract_summary(sub_text)
            sub_chunks.append(sub)
        return sub_chunks if sub_chunks else [chunk]

    # Multi-paragraph: split at paragraph boundaries
    sub_chunks = []
    buffer = []
    overlap_text = ""
    idx = 0

    for para in paragraphs:
        test_buf = buffer + [para]
        if token_count(overlap_text + "\n\n".join(test_buf)) > 700 and buffer:
            sub_text = (overlap_text + "\n\n".join(buffer)).strip()
            sub = dict(chunk)
            sub["text"] = sub_text
            sub["metadata"] = dict(chunk["metadata"])
            sub["metadata"]["chunk_id"] = f"{chunk['metadata']['chunk_id']}_{idx}"
            sub["metadata"]["token_count_approx"] = token_count(sub_text)
            sub["metadata"]["summary"] = extract_summary(sub_text)
            sub_chunks.append(sub)
            sentences = split_sentences("\n\n".join(buffer))
            tail = sentences[-overlap_sentences:] if len(sentences) >= overlap_sentences else sentences
            overlap_text = " ".join(tail) + "\n\n" if tail else ""
            buffer = [para]
            idx += 1
        else:
            buffer.append(para)

    if buffer:
        sub_text = (overlap_text + "\n\n".join(buffer)).strip()
        sub = dict(chunk)
        sub["text"] = sub_text
        sub["metadata"] = dict(chunk["metadata"])
        sub["metadata"]["chunk_id"] = f"{chunk['metadata']['chunk_id']}_{idx}"
        sub["metadata"]["token_count_approx"] = token_count(sub_text)
        sub["metadata"]["summary"] = extract_summary(sub_text)
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

def parse_whole_file(lines: list, file_path: str, doc_type: str) -> list:
    """Emit entire file as one chunk (adr, incident, page)."""
    title = parse_h1(lines)
    chunk = build_chunk(lines, file_path, doc_type, title, title, [], 0)
    return maybe_split_large_chunk(chunk)


def parse_glossary(lines: list, file_path: str) -> list:
    """
    1 term = 1 chunk.
    Terms are H3 blocks (### TermName).
    H2 sections (Domain Terms, Technical Terms, etc.) are breadcrumbs only.
    """
    title = parse_h1(lines)
    chunks = []
    current_h2 = ""
    buffer = []
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


def parse_api_endpoints(lines: list, file_path: str) -> list:
    """
    Overview H2 = 1 chunk.
    Each H3 (### METHOD /path) = 1 chunk.
    """
    title = parse_h1(lines)
    chunks = []
    current_h2 = ""
    buffer = []
    current_heading = ""
    current_level = 0  # track whether current buffer was opened by H2 or H3
    idx = 0

    def flush():
        nonlocal idx
        if buffer:
            parents = [current_h2] if (current_level == 3 and current_h2) else []
            c = build_chunk(buffer, file_path, "api_endpoint", title, current_heading, parents, idx)
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
                buffer = [line]
                current_h2 = text
                current_heading = text
                current_level = 2
            elif level == 3:
                flush()
                buffer = [line]
                current_heading = text
                current_level = 3
            else:
                buffer.append(line)
        else:
            buffer.append(line)

    flush()
    return chunks


def parse_features(lines: list, file_path: str) -> list:
    """
    Each H2 feature block = 1 chunk.
    If >600 tokens, split at H3 boundaries within the feature.
    """
    title = parse_h1(lines)
    chunks = []
    buffer = []
    current_heading = ""
    idx = 0

    def flush():
        nonlocal idx
        if not buffer or not current_heading:
            return
        text = "\n".join(buffer)
        if token_count(text) > 600:
            # split at H3 within this feature
            sub_buf = []
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


def parse_by_h2(lines: list, file_path: str, doc_type: str) -> list:
    """
    Generic and runbook: each H2 section = 1 chunk.
    If H2 > 600 tokens, split at H3 boundaries.
    """
    title = parse_h1(lines)
    chunks = []
    buffer = []
    current_h2 = ""
    idx = 0

    def flush():
        nonlocal idx
        if not buffer or not current_h2:
            return
        text = "\n".join(buffer)
        if token_count(text) > 600:
            sub_buf = []
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

def chunk_file(file_path: str, project_root: str) -> list:
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
        chunks = parse_whole_file(lines, rel, doc_type)
    elif doc_type == "glossary":
        chunks = parse_glossary(lines, rel)
    elif doc_type == "api_endpoint":
        chunks = parse_api_endpoints(lines, rel)
    elif doc_type == "feature":
        chunks = parse_features(lines, rel)
    elif doc_type in ("runbook", "generic"):
        chunks = parse_by_h2(lines, rel, doc_type)
    else:
        chunks = parse_whole_file(lines, rel, doc_type)

    # Drop chunks whose text is empty or too short to have a non-zero token count
    return [c for c in chunks if c["text"].strip() and c["metadata"]["token_count_approx"] > 0]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def find_md_files(root: str) -> list:
    """Return all .md files under root, sorted."""
    result = []
    for dirpath, _dirs, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith(".md"):
                result.append(os.path.join(dirpath, fname))
    return sorted(result)


def main():
    script_dir = Path(__file__).resolve().parent
    # script is at aidd-tasks/M3-rag/chunker/chunker.py
    # .parent      = aidd-tasks/M3-rag/chunker
    # .parent.parent     = aidd-tasks/M3-rag
    # .parent.parent.parent = aidd-tasks/  <-- project root
    project_root = script_dir.parent.parent  # M3-rag/chunker/ -> M3-rag/ -> aidd-tasks/
    data_dir = project_root / "docs" / "project-data"
    output_path = project_root / "M3-rag" / "chunks.jsonl"
    report_path = project_root / "M3-rag" / "report.md"

    md_files = find_md_files(str(data_dir))

    all_chunks = []
    stats = {}

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
    if stats:
        lines = lines[:-len(stats)] + ["| doc_type | count |", "|----------|-------|"] + lines[-len(stats):]
    else:
        lines.append("| doc_type | count |")
        lines.append("|----------|-------|")
        lines.append("| (none) | 0 |")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Done. {len(all_chunks)} chunks from {len(md_files)} files → {output_path}")
    print(f"Report → {report_path}")


if __name__ == "__main__":
    main()
