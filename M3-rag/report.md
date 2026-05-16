# Часть 2 — RAG на documentation corpus

Отчет о задании.

## Стек 
* Векторная БД  postgres + pgvector
* Модель для embedding/search - локальная ollama bge-m3
   
## Chunking
* **Script** `M3-rag/chunker/chunker.py`
* **Files processed:** 47
* **Total chunks:** 457
* **Output:** `M3-rag/chunks.jsonl`

Chunks by doc_type

| doc_type | count |
|----------|-------|
| `adr` | 17 |
| `api_endpoint` | 69 |
| `feature` | 60 |
| `generic` | 179 |
| `glossary` | 41 |
| `incident` | 11 |
| `page` | 15 |
| `runbook` | 65 |

## Embedding

**Script** `M3-rag/embedder.py`

**Output:** postgres with pgvector extension

## Search
* **Script** `M3-rag/embedder.py`
* **Output:**
`python3 query.py "Текущие проблемы proshop mern" 5`

[1] score=0.6377
source: best-practices.md
type:   generic
heading: 1. Introduction: Why proshop_mern Is Deprecated
text:  ## 1. Introduction: Why proshop_mern Is Deprecated

The original `proshop_mern` fork (bradtraversy/proshop_mern) was built circa 2020–2022 with:

- **React 17** — predates concurrent rendering and Server Components
- **Create React App** — unmaintain... [truncated]

  [2] score=0.5864
  source: local-setup.md
  type:   runbook
  heading: 1. Clone Repository
  text:  ### 1. Clone Repository

```bash
git clone <repository-url> proshop-mern
cd proshop-mern
```

Verify you're in the root directory by checking for `package.json`:

```bash
ls package.json  # Should print "package.json"
```

[3] score=0.5776
source: architecture.md
type:   generic
heading: 1. System Overview
text:  ## 1. System Overview

ProShop is a full-stack e-commerce web application built with the MERN stack
(MongoDB, Express, React, Node). It ships a working storefront where customers
browse a product catalogue, build a cart, authenticate, complete a mult... [truncated]

[4] score=0.5692
source: feature-flags-spec.md
type:   generic
heading: Feature Flags in This Project
text:  ### Feature Flags in This Project

The ProShop MERN codebase is a teaching project: a full-stack e-commerce application built with MongoDB, Express, React, and Node.js. It contains a product catalog, shopping cart, multi-step checkout, PayPal payment... [truncated]

