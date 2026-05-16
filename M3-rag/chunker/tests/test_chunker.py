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
    assert detect_language("Feature: Admin Panel. Назначение: управление.") == "ru"


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
