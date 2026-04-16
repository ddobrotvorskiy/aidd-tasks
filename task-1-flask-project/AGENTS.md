# AGENTS.md — Coding Agent Guidelines

This is a corporate employee directory application built with:
- **Backend:** Python / Flask
- **Frontend:** React.js
- **Database:** PostgreSQL
- **Infrastructure:** Docker Compose

No existing cursor rules, copilot instructions, or prior AGENTS.md were found; these conventions are established for greenfield development.

---

## Project Structure

```
task-1-flask-project/
├── backend/               # Flask application
│   ├── app/
│   │   ├── __init__.py    # App factory (create_app)
│   │   ├── models/        # SQLAlchemy models
│   │   ├── routes/        # Blueprint route handlers
│   │   ├── schemas/       # Marshmallow / Pydantic schemas
│   │   ├── services/      # Business logic layer
│   │   └── utils/         # Shared helpers
│   ├── tests/
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/              # React application (Vite + TypeScript)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── api/           # API client / hooks
│   │   └── types/
│   ├── package.json
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

### Backend (Flask)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

flask db upgrade                   # apply migrations
flask run --debug                  # development server (port 5000)
```

### Frontend (React)
```bash
cd frontend
npm install
npm run dev                        # development server (port 5173)
npm run build                      # production build
npm run lint                       # ESLint check
npm run type-check                 # tsc --noEmit
```

---

## Testing Commands

### Backend (pytest)
```bash
cd backend
pytest                             # run all tests
pytest tests/test_auth.py          # run a single test file
pytest tests/test_auth.py::test_login_success  # run a single test
pytest -x                          # stop at first failure
pytest -v                          # verbose output
pytest --cov=app --cov-report=term-missing  # with coverage
```

### Frontend (Vitest)
```bash
cd frontend
npm test                           # run all tests (watch mode)
npm run test:run                   # run all tests once (CI)
npm run test -- src/components/EmployeeCard.test.tsx  # single file
```

### Linting
```bash
cd backend
ruff check .                       # Python linting (preferred over flake8)
ruff format --check .              # Python formatting check
mypy app/                          # type checking

cd frontend
npm run lint                       # ESLint
```

---

## Python / Flask Code Style

### Formatting and Linting
- Use **Ruff** for linting and formatting (`ruff check`, `ruff format`).
- Line length: **88** characters (Black-compatible default).
- Target Python **3.11+**.

### Imports
- Group imports: stdlib → third-party → local. Separated by blank lines.
- Use absolute imports within the `app` package; never relative imports across packages.
- Import specific names rather than whole modules where practical.

```python
# Good
from flask import Blueprint, jsonify, request
from app.models.user import User
from app.services.auth import AuthService
```

### Type Hints
- All function signatures must include type hints (parameters and return type).
- Use `from __future__ import annotations` at the top of every module.
- Use `Optional[X]` or `X | None` (prefer the latter on Python 3.10+).
- Use `TypedDict` or dataclasses for structured data passed between layers.

```python
from __future__ import annotations

def get_employee(employee_id: int) -> Employee | None:
    ...
```

### Naming Conventions
| Construct | Convention | Example |
|-----------|-----------|---------|
| Modules / files | `snake_case` | `employee_service.py` |
| Classes | `PascalCase` | `EmployeeService` |
| Functions / methods | `snake_case` | `get_employee_by_id` |
| Variables | `snake_case` | `employee_list` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_PAGE_SIZE = 100` |
| Flask Blueprints | `snake_case` variable, `kebab-case` URL prefix | `employees_bp`, `/employees` |

### Error Handling
- Use Flask error handlers registered on the app or blueprint, not bare `try/except` in routes.
- Return JSON error responses consistently: `{"error": "message", "code": "ERROR_CODE"}`.
- Raise domain-specific exceptions in the service layer; catch them in routes.
- Never swallow exceptions silently — always log with `current_app.logger`.

```python
# Service layer
class EmployeeNotFoundError(Exception):
    pass

# Route layer
@bp.errorhandler(EmployeeNotFoundError)
def handle_not_found(e: EmployeeNotFoundError):
    return jsonify({"error": str(e), "code": "NOT_FOUND"}), 404
```

### Models (SQLAlchemy)
- One model per file under `app/models/`.
- Define `__tablename__` explicitly.
- Use `db.Mapped` / `mapped_column` (SQLAlchemy 2.x style).
- Never put business logic in models — delegate to services.

### API Design
- REST conventions: nouns for resources, HTTP verbs for actions.
- All endpoints return JSON; use 201 for creation, 204 for deletion.
- Validate and deserialize request bodies with Marshmallow or Pydantic schemas before passing to services.
- Paginate list endpoints; default page size: 20, max: 100.

---

## React / TypeScript Code Style

### Formatting
- **Prettier** for formatting; **ESLint** with `eslint-config-airbnb-typescript` for linting.
- Use **TypeScript** — no plain `.js` files in `src/`.
- Avoid `any`; use proper types or `unknown` with runtime narrowing.

### Components
- One component per file; filename matches the component name (`EmployeeCard.tsx`).
- Use **functional components** with hooks only; no class components.
- Keep components small and focused; extract logic into custom hooks (`useEmployees`, `useAuth`).
- Co-locate component-specific styles, tests, and types in the same directory.

### Naming Conventions
| Construct | Convention | Example |
|-----------|-----------|---------|
| Components | `PascalCase` | `EmployeeCard` |
| Hooks | `camelCase` prefixed `use` | `useEmployee` |
| Files (components) | `PascalCase.tsx` | `EmployeeCard.tsx` |
| Files (utils/hooks) | `camelCase.ts` | `useEmployee.ts` |
| CSS classes | `kebab-case` | `employee-card__avatar` |

### API Calls
- Centralise all API calls under `src/api/`; never call `fetch`/`axios` directly in components.
- Use **React Query** (`@tanstack/react-query`) for data fetching, caching, and mutation.
- Type all API responses with interfaces in `src/types/`.

### Error Handling (Frontend)
- Use React Query's `onError` / `isError` states for async errors.
- Display user-facing error messages via a shared `<Toast>` / `<Alert>` component.
- Never log sensitive user data to the console in production.

---

## Database Conventions

- Use **Flask-Migrate** (Alembic) for all schema changes; never mutate the schema manually.
- Every migration must be reversible (implement `downgrade()`).
- Use database-level constraints (NOT NULL, UNIQUE, FK) to enforce data integrity.
- Store passwords hashed with `bcrypt`; never store plaintext credentials.
- User-uploaded photos: store on disk / object storage; store only the path/URL in the DB.

---

## Environment and Secrets

- All secrets (DB URL, secret key, etc.) come from environment variables — never hardcoded.
- Use a `.env` file locally (gitignored); document required variables in `.env.example`.
- Required backend variables: `DATABASE_URL`, `SECRET_KEY`, `FLASK_ENV`.

---

## Git Conventions

- Branch names: `feature/<short-description>`, `fix/<short-description>`.
- Commit messages follow Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`.
- All tests must pass before merging to `main`.
