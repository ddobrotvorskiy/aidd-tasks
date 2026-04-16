# AGENTS.md — Coding Agent Guidelines

Corporate employee directory app: **Flask** backend, **React/TypeScript** frontend, **PostgreSQL** database, **Docker Compose** infrastructure.

No Cursor rules, Copilot instructions, or `.editorconfig` are present in this repo.

---

## Project Structure

```
task-1-flask-project/
├── backend/
│   ├── app/
│   │   ├── __init__.py        # App factory: create_app, extension init
│   │   ├── config.py          # pydantic-settings Settings class
│   │   ├── models/            # SQLAlchemy 2.x models (one per file)
│   │   ├── routes/            # Flask Blueprint handlers + errors.py
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/          # Business logic + exceptions.py
│   │   └── utils/             # Shared helpers
│   ├── migrations/            # Alembic migration files
│   ├── tests/                 # pytest test suite
│   ├── requirements.txt
│   └── pyproject.toml         # ruff, mypy, pytest, coverage config
├── frontend/
│   ├── src/
│   │   ├── api/               # Axios client + per-resource modules
│   │   ├── components/        # Reusable React components
│   │   ├── contexts/
│   │   ├── hooks/             # Custom React hooks
│   │   ├── pages/             # Route-level page components
│   │   └── types/             # Shared TypeScript interfaces
│   ├── eslint.config.js       # ESLint v9 flat config
│   ├── tsconfig.app.json      # Strict TS settings (target: es2023)
│   └── vite.config.ts
├── docker-compose.yml
└── AGENTS.md
```

---

## Build / Run Commands

### Docker Compose (full stack)
```bash
docker compose up --build          # build and start all services
docker compose up -d               # start in background
docker compose down                # stop and remove containers
docker compose logs -f backend     # tail backend logs
```

### Backend (Flask — Python 3.12)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
flask db upgrade                   # apply Alembic migrations
flask run --debug                  # dev server on port 5000
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev                        # dev server on port 5173
npm run build                      # tsc -b + vite build (production)
npm run lint                       # ESLint check
npm run preview                    # serve the production build locally
```

> **Note:** There is no frontend test runner configured yet (Vitest is not installed).
> `npm run type-check` is not a defined script — use `npm run build` to get tsc errors.

---

## Testing Commands

### Backend (pytest)
```bash
cd backend
pytest                                          # run all tests
pytest tests/test_auth.py                       # single test file
pytest tests/test_auth.py::test_login_success   # single test function
pytest -x                                       # stop at first failure
pytest -v                                       # verbose (default via addopts)
pytest --cov=app --cov-report=term-missing      # with coverage
```

### Linting and Type Checking
```bash
# Backend
cd backend
ruff check .                       # lint (preferred over flake8)
ruff format --check .              # formatting check
mypy app/                          # type checking

# Frontend
cd frontend
npm run lint                       # ESLint (v9 flat config)
```

---

## Python / Flask Code Style

### Formatting and Linting
- **Ruff** handles both linting and formatting (`ruff check`, `ruff format`).
- Line length: **88** characters (Black-compatible).
- Target: **Python 3.12**. Enabled rule sets: `E`, `F`, `I` (isort), `UP`, `B`, `SIM`.
- `from __future__ import annotations` at the top of **every** module.

### Imports
```python
# stdlib → third-party → local, separated by blank lines
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.models.user import User
from app.services.employee_service import EmployeeService
```
- Use **absolute imports** within `app`; never relative cross-package imports.
- `known-first-party = ["app"]` is configured in pyproject.toml for isort.

### Type Hints
- All function signatures must have typed parameters **and** return types.
- Prefer `X | None` over `Optional[X]`.
- Use Pydantic models or `TypedDict` for structured data between layers.

```python
from __future__ import annotations

def get_employee(employee_id: int) -> Employee | None:
    ...
```

### Naming Conventions
| Construct | Convention | Example |
|---|---|---|
| Modules / files | `snake_case` | `employee_service.py` |
| Classes | `PascalCase` | `EmployeeService` |
| Functions / methods | `snake_case` | `get_employee_by_id` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_PAGE_SIZE = 100` |
| Flask Blueprints | `snake_case` var, `kebab-case` prefix | `employees_bp`, `/employees` |

### Error Handling
- All domain exceptions inherit from `AppError` (defined in `services/exceptions.py`) with `http_status` and `code` class attributes.
- Raise exceptions in the **service layer**; never put business-logic `try/except` in routes.
- All exceptions are caught by `register_error_handlers(app)` in `routes/errors.py`.
- JSON error shape: `{"error": "<message>", "code": "<ERROR_CODE>"}`.
- Never swallow exceptions silently — log with `current_app.logger`.

```python
# services/exceptions.py
class NotFoundError(AppError):
    http_status = 404
    code = "NOT_FOUND"

# routes/errors.py  (registered once on the app, not per blueprint)
@app.errorhandler(AppError)
def handle_app_error(e: AppError) -> tuple[Response, int]:
    return jsonify({"error": str(e), "code": e.code}), e.http_status
```

### Models (SQLAlchemy 2.x)
- One model per file under `app/models/`.
- Define `__tablename__` explicitly; use `db.Mapped` / `mapped_column`.
- No business logic in models — delegate everything to services.

### API Design
- REST conventions: noun resources, HTTP verbs for actions.
- Return JSON always; use **201** for creation, **204** for deletion.
- Validate request bodies with **Pydantic** schemas before passing to services.
- Paginate list endpoints: default page size **20**, max **100**.

---

## React / TypeScript Code Style

### Tooling
- **ESLint v9** (flat config in `eslint.config.js`) with `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`.
- **TypeScript** strict settings: `noUnusedLocals`, `noUnusedParameters`, `verbatimModuleSyntax`.
- No Prettier configured — formatting is not currently enforced by tooling.
- No plain `.js` files in `src/`; no `any` — use proper types or `unknown` with narrowing.

### Components
- One component per file; filename **must** match the component name (`EmployeeCard.tsx`).
- **Functional components** with hooks only — no class components.
- Keep components focused; extract reusable logic into custom hooks.
- UI components use **Ant Design** (`antd`) — prefer its primitives over custom CSS.

### Naming Conventions
| Construct | Convention | Example |
|---|---|---|
| Components | `PascalCase` | `EmployeeCard` |
| Hooks | `camelCase` prefixed `use` | `useEmployee` |
| Component files | `PascalCase.tsx` | `EmployeeCard.tsx` |
| Hook / util files | `camelCase.ts` | `useEmployee.ts` |

### API Calls
- All HTTP calls go through the centralised **Axios instance** in `src/api/client.ts` (handles JWT attachment and 401 redirects).
- Resource-specific functions live in `src/api/<resource>.ts` — **never** call axios directly in components.
- Use **React Query** (`@tanstack/react-query`) for data fetching, caching, and mutations.
- Type all API responses with interfaces in `src/types/index.ts`.

### Error Handling (Frontend)
- Use React Query's `isError` / `error` states for async error display.
- Show user-facing messages via Ant Design `message` or `notification` utilities.
- Never log sensitive data to the console in production builds.

---

## Database Conventions

- Use **Flask-Migrate** (Alembic) for all schema changes — never alter the schema manually.
- Every migration must implement a working `downgrade()`.
- Enforce data integrity with DB-level constraints (NOT NULL, UNIQUE, FK).
- Passwords hashed with **bcrypt** (`Flask-Bcrypt`) — never store plaintext.
- Uploaded photos: store on disk/object storage; persist only the path/URL in the DB.

---

## Environment and Secrets

- All secrets come from environment variables — never hardcoded.
- Use a `.env` file locally (gitignored); keep `.env.example` up to date.
- Required backend variables: `DATABASE_URL`, `SECRET_KEY`, `FLASK_ENV`.

---

## Git Conventions

- Branch names: `feature/<short-description>` or `fix/<short-description>`.
- Commit messages follow **Conventional Commits**: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`.
- All backend tests must pass (`pytest`) before merging to `main`.
