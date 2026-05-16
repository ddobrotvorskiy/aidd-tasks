# M3-rag — Semantic Search on Project Documentation

RAG-пайлайн для индексации и семантического поиска по документации:
**ingest → embed → query**.

Full pipeline:
```
docs/project-data/**/*.md ──▶ chunker ──▶ chunks.jsonl ──▶ embedder ──▶ PostgreSQL (pgvector)
                                                                                                   │
                                          query.py ◀────────────────────────────────────────────────┘
                                          (embed + cosine search)
```

## Prerequisites

| Требование | Команда | Порт |
|------------|---------|------|
| **Ollama** с моделью bge-m3 | `ollama pull bge-m3` | 11434 |
| **PostgreSQL + pgvector** | `docker run -p 35432:5432 pgvector/pgvector:pg17` | 35432 |
| **Python 3.10+** | — | — |
| **psycopg2** | `pip install psycopg2-binary` | — |

## `.env`

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=12345
POSTGRES_DB=postgres
DATABASE_URL=postgresql://postgres:12345@localhost:35432/postgres
```

---

## 1. Chunker — разбиение документов

```bash
python chunker/chunker.py
```

**Вход:** `docs/project-data/**/*.md`

**Выход:** `chunks.jsonl` (по 1 JSON line на чанк) + `report.md`

### Как работает

1. Обходит все `.md` в `docs/project-data/`
2. Классифицирует doc_type по пути файла
3. Парсит по-разному в зависимости от типа (см. ниже)
4. Разбивает секции на чанки ≤700 токенов (~2800 символов), с overlap 2 предложений на границах
5. Извлекает метаданные: keywords, summary, token count, language

### Doc types и стратегии парсинга

| Doc type | Путь | Стратегия |
|----------|------|-----------|
| `adr` | `adrs/adr-*.md` | Весь файл → 1+ чанков |
| `incident` | `incidents/i-*.md` | Весь файл → 1+ чанков |
| `page` | `pages/*.md` | Весь файл → 1+ чанков |
| `glossary` | `glossary.md` | По термину (H3) |
| `api_endpoint` | `api/*.md` | По endpoint (H2 overview + H3 per-route) |
| `feature` | `features/*.md` | По фиче (H2); сплит на H3 при >600 tokens |
| `runbook` | `runbooks/*.md` | По секции (H2); сплит на H3 при >600 tokens |
| `generic` | Остальные `.md` | По секции (H2); сплит на H3 при >600 tokens |

### Методы

```python
chunk_file(file_path, project_root)   → list[dict]
find_md_files(root)                   → list[str]
```

### Тесты

```bash
pytest -q chunker/tests/
```

### Формат чанка

```json
{
  "text": "# ADR-001: Use MongoDB...",
  "metadata": {
    "chunk_id": "docs_project_data_adrs_adr_001...__0",
    "source_file": "adr-001-mongodb-vs-postgres.md",
    "file_path": "docs/project-data/adrs/adr-001-mongodb-vs-postgres.md",
    "doc_type": "adr",
    "title": "ADR-001: Use MongoDB (via Mongoose) as the Primary Database",
    "section_heading": "ADR-001: Use MongoDB (via Mongoose) as the Primary Database",
    "parent_headings": [],
    "language": "en",
    "keywords": ["adr", "use", "mongodb", "via", "mongoose", "primary", "database"],
    "summary": "Before the first commit, the team needed to select a database for the ProShop e-commerce application.",
    "token_count_approx": 424
  }
}
```

---

## 2. Embedder — эмбеддинг и сохранение в Postgres

```bash
python embedder.py
```

**Вход:** `chunks.jsonl`

**Выход:** `chunks_embedded.jsonl` + запись в Postgres (таблица `rag_chunks`)

### Как работает

1. Читает чанки из `chunks.jsonl`
2. Батчит по 32 чанка и вызывает Ollama `/api/embed` с моделью `bge-m3` (1024-dim вектор)
3. Записывает вектор эмбеддинга в каждый чанк
4. Сохраняет все чанки в Postgres:
   - `VECTOR(1024)` колонка + HNSW индекс (`m=16, ef_construction=64`)
   - Индекс по `doc_type` для pre-filter
5. Поддерживает resumable runs через `.embed_progress.json` — при повторном запуске пропускает уже вставленные чанки
6. На успешном завершении чистит `.embed_progress.json`

### Схема таблицы

```sql
CREATE TABLE rag_chunks (
    chunk_id           TEXT PRIMARY KEY,
    source_file        TEXT,
    file_path          TEXT,
    doc_type           TEXT,
    title              TEXT,
    section_heading    TEXT,
    parent_headings    TEXT[],
    language           TEXT,
    keywords           TEXT[],
    summary            TEXT,
    token_count_approx INTEGER,
    text               TEXT,
    embedding          VECTOR(1024),
    created_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rag_chunks_embedding ON rag_chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_rag_chunks_doctype ON rag_chunks USING btree (doc_type);
```

### API

```python
load_chunks(path: Path)               → list[dict]
call_ollama(texts: list)              → list[list[float]]  # batch embeddings
embed_chunks(chunks, batch_size=32)   → list[dict]
save_to_postgres(chunks, db_url)      → int                # rows inserted
write_output(chunks, path)            # writes chunks_embedded.jsonl
```

### Настройки

| Константа | Значение | Описание |
|-----------|----------|----------|
| `MODEL` | `"bge-m3"` | Ollama embedding model |
| `BATCH_SIZE` | `32` | Текстов за один запрос к Ollama |
| `PG_BATCH` | `100` | Чанков за один INSERT в Postgres |

---

## 3. Query — семантический поиск

```bash
python query.py [query] [top_k] [--type DOC_TYPE] [--source SOURCE_FILE]
```

### Как работает

1. **Embed** — отправляет запрос в Ollama (`bge-m3`), получает 1024-dim вектор (та же модель, что при ingestion)
2. **Search** — cosine similarity (`1 - (embedding <=> query_vec)`) по таблице `rag_chunks`
3. **Filter** — опционально pre-filter по `doc_type` и/или `source_file`
4. **Return** — top-K результатов с метаданными и текстом (обрезанным до 500 символов)

### Функция `search(query, top_k, doc_type, source_file)`

```python
from query import search

# Базовый поиск
results = search("Какая БД используется в proshop_mern и почему именно она?", top_k=5)

# С фильтром по типу (только ADR)
results = search("Какая БД используется в proshop_mern?", top_k=5, doc_type="adr")

# С фильтром по конкретному файлу
results = search("MongoDB или PostgreSQL?", top_k=5, source_file="adr-001-mongodb-vs-postgres.md")
```

Возвращает:

```python
[{
    "score": 0.6446,           # cosine similarity, 0..1
    "chunk_id": "docs_project_...",
    "source_file": "adr-001-mongodb-vs-postgres.md",
    "file_path": "docs/project-data/adrs/adr-001-mongodb-vs-postgres.md",
    "doc_type": "adr",
    "title": "ADR-001: ...",
    "section_heading": "ADR-001: ...",
    "text": "# ADR-001: Use MongoDB... [truncated at 500 chars]",
}]
```

### Примеры CLI

```bash
# Демо: 3 тестовых запроса
python query.py

# Один запрос, top-5
python query.py "Какая БД используется в proshop_mern?"

# Один запрос, top-3
python query.py "Какие фичи зависят от search_v2?" 3

# Query с фильтром по doc_type
python query.py "incident с checkout" 5 --type incident

# Query с фильтром по source_file
python query.py "Redux vs Context" 5 --type adr

# Query с фильтром по обоим параметрам
python query.py "semantic search" 5 --type feature --source feature-flags-spec.md
```

### API

```python
embed_query(text: str)              → list[float]  # 1024-dim vector
search(query, top_k=5, doc_type=None, source_file=None) → list[dict]
run_demo()                          # runs 3 canonical test queries
```

---

## Полный цикл

```bash
# 1. Чанки
python chunker/chunker.py

# 2. Эмбеддинг + Postgres
python embedder.py

# 3. Поиск
python query.py                      # демо
python query.py "your question" 5    # один запрос
```

## Структура проекта

```
M3-rag/
├── chunker/
│   ├── chunker.py          # Markdown parser + classifier + chunk builder
│   └── tests/
│       └── test_chunker.py # Unit tests
├── embedder.py             # Ollama embedder + Postgres writer
├── query.py                # Semantic search CLI + API
├── docs/project-data/      # Source markdown documents
├── chunks.jsonl            # Generated by chunker
├── chunks_embedded.jsonl   # Generated by embedder (safe to delete)
├── .embed_progress.json    # Resumable state (auto-cleaned on success)
├── report.md               # Chunking report
├── .env                    # PostgreSQL connection
├── AGENTS.md               # Agent context
└── README.md               # This file
```
