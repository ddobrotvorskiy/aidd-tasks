import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from chunker import (
    detect_language,
    extract_keywords,
    extract_summary,
    token_count,
    slugify,
    split_sentences,
    maybe_split_large_chunk,
    build_chunk,
    chunk_file,
    classify_doc_type,
    parse_glossary,
    parse_api_endpoints,
    parse_features,
    parse_whole_file,
    parse_by_h2,
)


def test_detect_language_english():
    assert detect_language("The product catalog with pagination and keyword search.") == "en"


def test_detect_language_russian():
    assert detect_language("Покрывает управление товарами и пользователями в административной панели.") == "ru"


def test_detect_language_mixed_mostly_english():
    # less than 30% cyrillic — e.g. one Russian word among many English words
    assert detect_language("The product catalog with search and pagination. Добавить.") == "en"


def test_detect_language_mixed_mostly_russian():
    # more than 30% cyrillic
    assert detect_language("Назнач��ние: управление товарами. Admin panel feature.") == "ru"


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


def test_maybe_split_large_chunk_adds_suffix():
    # Build a chunk with ~1000 tokens (4000 chars), split across two paragraphs
    para = "word " * 400  # ~2000 chars → ~500 tokens each paragraph
    big_text = para.strip() + "\n\n" + para.strip()
    chunk = build_chunk(
        [big_text], "docs/project-data/architecture.md", "generic",
        "Title", "Section", [], 0
    )
    result = maybe_split_large_chunk(chunk)
    assert len(result) >= 2
    for r in result:
        assert "_" in r["metadata"]["chunk_id"].split("__")[-1]  # has suffix


def test_maybe_split_large_chunk_small_unchanged():
    small_text = "Short text."
    chunk = build_chunk(
        [small_text], "docs/project-data/architecture.md", "generic",
        "Title", "Section", [], 0
    )
    result = maybe_split_large_chunk(chunk)
    assert len(result) == 1
    # chunk_id should NOT have a suffix added
    assert result[0]["metadata"]["chunk_id"] == chunk["metadata"]["chunk_id"]


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


def test_parse_api_endpoints_overview_has_no_parent():
    lines = [
        "# Orders API",
        "## Overview",
        "Manages order lifecycle.",
        "## Endpoints",
        "### POST /api/orders",
        "Create order.",
    ]
    chunks = parse_api_endpoints(lines, "docs/project-data/api/orders.md")
    overview_chunk = next(c for c in chunks if c["metadata"]["section_heading"] == "Overview")
    assert overview_chunk["metadata"]["parent_headings"] == []


def test_parse_api_endpoints_endpoint_has_h2_parent():
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


def test_parse_features_large_feature_splits_at_h3():
    # A feature > 600 tokens should split at H3 boundaries
    # token_count = len(text) // 4; "word " = 5 chars → 300 reps = 375 tokens each,
    # combined ~760 tokens total which exceeds the 600-token threshold
    big_para = "word " * 300
    lines = [
        "# Features",
        "## Feature 1: Big Feature",
        "### Section A",
        big_para,
        "### Section B",
        big_para,
    ]
    chunks = parse_features(lines, "docs/project-data/features/admin.md")
    # Should have produced at least 2 chunks (one per H3)
    assert len(chunks) >= 2


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
    # token_count = len(text) // 4; "word " = 5 chars → 300 reps = 375 tokens each,
    # combined ~760 tokens total which exceeds the 600-token threshold
    big_para = "word " * 300
    lines = [
        "# Doc",
        "## Big Section",
        "### Sub A",
        big_para,
        "### Sub B",
        big_para,
    ]
    chunks = parse_by_h2(lines, "docs/project-data/architecture.md", "generic")
    # Should have split into at least 2 chunks
    assert len(chunks) >= 2


# --- INDEX.md skipped ---

def test_index_md_skipped(tmp_path):
    index = tmp_path / "INDEX.md"
    index.write_text("# Index\n\nSome content.\n")
    chunks = chunk_file(str(index), str(tmp_path))
    assert chunks == []


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
