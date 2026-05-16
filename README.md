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
