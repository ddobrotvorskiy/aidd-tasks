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
