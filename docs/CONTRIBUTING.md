# Contributing to GlacierNET-KZ

> Development setup, code standards, and contribution workflow.
> See also: [`API_REFERENCE.md`](./API_REFERENCE.md) | [`ARCHITECTURE.md`](./ARCHITECTURE.md)

## Table of Contents

- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Clone & Install](#clone--install)
  - [Environment Variables](#environment-variables)
  - [Run Locally](#run-locally)
- [Project Structure](#project-structure)
- [Code Standards](#code-standards)
  - [Python (Backend)](#python-backend)
  - [TypeScript (Frontend)](#typescript-frontend)
- [Git Workflow](#git-workflow)
  - [Branch Naming](#branch-naming)
  - [Commit Messages](#commit-messages)
  - [Pull Requests](#pull-requests)
- [Testing](#testing)
  - [Backend Tests](#backend-tests)
  - [Frontend Tests](#frontend-tests)
- [How-To Guides](#how-to-guides)
  - [Add a New API Endpoint](#add-a-new-api-endpoint)
  - [Add a New Frontend Page](#add-a-new-frontend-page)
  - [Add a New ML Model](#add-a-new-ml-model)
  - [Add a New MCP Tool](#add-a-new-mcp-tool)
- [Review Checklist](#review-checklist)

---

## Getting Started

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| Docker | 24+ | Compose deployment |
| Docker Compose | v2+ | Multi-service orchestration |
| Redis | 7+ | Rate limiting (optional for local dev) |
| ruff | latest | Python linting |
| pytest | latest | Python testing |

### Clone & Install

```bash
git clone https://github.com/your-org/GlacierNET-KZ.git
cd GlacierNET-KZ

# Backend
cd glacierkz-api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend
cd ../glacierkz-web
npm install

# MCP Server (optional)
cd ../glacierkz-mcp
pip install -r requirements.txt
```

### Environment Variables

Create `glacierkz-api/.env`:

```env
# Required
API_KEYS_FILE=app/permissions/api_keys.json
JWT_SECRET_KEY=your-secret-key-here
RESULTS_DIR=./results

# Optional — LLM
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=sk-...

# Optional — Redis (falls back to in-memory if unavailable)
REDIS_URL=redis://localhost:6379

# CORS
CORS_ORIGINS=http://localhost:3000
```

### Run Locally

```bash
# Start Redis (optional)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Backend
cd glacierkz-api
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd glacierkz-web
npm run dev
```

Access:
- API docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

---

## Project Structure

```
GlacierNET-KZ/
├── glacierkz-api/               # FastAPI backend
│   ├── app/
│   │   ├── main.py              # App initialization, middleware, routers
│   │   ├── config.py            # Environment variable loading
│   │   ├── auth/                # Authentication modules
│   │   │   ├── api_key.py       # API key validation
│   │   │   ├── jwt_auth.py      # JWT token handling
│   │   │   └── rbac.py          # Role-based access control
│   │   ├── routes/              # Management endpoints
│   │   │   ├── tasks.py         # Task CRUD and lifecycle
│   │   │   ├── datasets.py      # Dataset management
│   │   │   ├── training.py      # Model training
│   │   │   └── monitoring.py    # Health and metrics
│   │   ├── routers/             # Prediction endpoints
│   │   │   ├── segmentation.py  # Image segmentation
│   │   │   ├── compare.py       # Multi-model comparison
│   │   │   ├── trend.py         # Temporal trend analysis
│   │   │   ├── export.py        # Result export
│   │   │   └── history.py       # Prediction history
│   │   ├── services/            # Business logic
│   │   ├── schemas/             # Pydantic models
│   │   │   ├── requests.py      # Request schemas
│   │   │   └── responses.py     # Response schemas
│   │   ├── middleware/           # Request pipeline
│   │   │   ├── rate_limit.py    # Token-bucket throttling
│   │   │   ├── security_headers.py  # CSP, HSTS, etc.
│   │   │   ├── request_logging.py   # Structured access logs
│   │   │   └── cache.py         # Response caching
│   │   ├── monitoring/          # Observability
│   │   │   └── health.py        # HealthChecker
│   │   └── ws/                  # WebSocket
│   │       ├── handlers.py      # Message routing
│   │       └── manager.py       # ConnectionManager
│   ├── tests/                   # Backend tests
│   ├── pyproject.toml           # Project config (ruff, pytest)
│   └── Dockerfile
├── glacierkz-web/               # Next.js frontend
│   ├── src/
│   │   ├── app/                 # Page routes
│   │   │   ├── layout.tsx       # Root layout
│   │   │   ├── page.tsx         # Landing page
│   │   │   ├── analysis/        # Segmentation page
│   │   │   ├── compare/         # Comparison page
│   │   │   ├── dashboard/       # Dashboard page
│   │   │   ├── datasets/        # Dataset management
│   │   │   ├── history/         # Prediction history
│   │   │   ├── predict/         # Single prediction
│   │   │   ├── reports/         # Report generation
│   │   │   ├── settings/        # Settings page
│   │   │   ├── training/        # Training page
│   │   │   └── trend/           # Time series page
│   │   ├── components/          # Reusable UI components
│   │   ├── lib/                 # Utilities
│   │   │   ├── api.ts           # API client functions
│   │   │   ├── i18n.ts          # ru/en translations
│   │   │   └── utils.ts         # Helper functions
│   │   └── store/               # Zustand state
│   ├── package.json
│   └── Dockerfile
├── glacierkz-mcp/               # MCP tool server
│   ├── server.py                # MCP server with 10 tools
│   └── README.md
├── satellite_data/              # Raw satellite imagery
├── results/                     # Prediction outputs
├── docker-compose.yml           # Service orchestration
└── pyproject.toml               # Root project config
```

---

## Code Standards

### Python (Backend)

**Linter:** Ruff (configured in `pyproject.toml`)

```toml
[tool.ruff]
line-length = 120
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "A", "SIM"]
ignore = ["E501"]
```

**Run linting:**

```bash
ruff check glacierkz-api/
ruff format glacierkz-api/
```

**Style rules:**
- Max line length: 120 characters
- Use type hints on all function signatures
- Prefer `from __future__ import annotations` for forward references
- Pydantic models for all request/response schemas
- `async def` for all route handlers (even if not I/O-bound)
- Use `Path` over string concatenation for file paths
- No comments unless explaining non-obvious logic
- Docstrings: Google-style for public functions only

**Naming:**
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Routes: `kebab-case` or `snake_case` (match existing)

### TypeScript (Frontend)

**Formatter:** Prettier (via Next.js)
**Linter:** ESLint (via Next.js)

**Style rules:**
- 2-space indentation
- Single quotes for strings
- Trailing commas in multi-line structures
- No semicolons (unless needed for ASI)
- Prefer `const` over `let`
- Named exports over default exports
- Interfaces over type aliases for object shapes
- No `any` — use `unknown` and narrow

**Component conventions:**
- Functional components only (no class components)
- Props interfaces named `{ComponentName}Props`
- Client components marked with `'use client'` at top
- Co-locate component files: `ComponentName.tsx` + `ComponentName.test.tsx`

---

## Git Workflow

### Branch Naming

| Pattern | Purpose |
|---------|---------|
| `feature/description` | New feature |
| `fix/description` | Bug fix |
| `refactor/description` | Code refactoring |
| `docs/description` | Documentation only |
| `test/description` | Test additions/fixes |

Examples:
```
feature/add-ndsi-threshold-slider
fix/segmentation-mask-overlay-blend
refactor/extract-health-checker-service
docs/add-api-reference
```

### Commit Messages

Follow Conventional Commits:

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`

**Examples:**

```
feat(routers): add CRF post-processing toggle to segmentation endpoint
fix(ws): prevent room leak when client disconnects during broadcast
refactor(services): extract area calculation into dedicated utility
docs: add API reference for monitoring endpoints
test(segmentation): add TTA flip augmentation tests
chore: update ruff config to include B and A rules
```

### Pull Requests

1. Create a feature branch from `main`
2. Make changes in small, focused commits
3. Run linting and tests before pushing
4. Open PR with a descriptive title and summary
5. Link related issues if applicable
6. Request review from at least one maintainer
7. Address feedback, squash if needed
8. Merge after approval + green CI

**PR title format:** Same as commit messages — `<type>(<scope>): <description>`

**PR description should include:**
- What changed and why
- How to test the change
- Screenshots for UI changes
- Breaking changes or migration notes (if any)

---

## Testing

### Backend Tests

```bash
cd glacierkz-api

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_segmentation.py -v

# Run tests matching a pattern
pytest tests/ -k "test_predict" -v
```

**Test conventions:**
- Tests live in `glacierkz-api/tests/`
- File naming: `test_<module>.py`
- Function naming: `test_<function_name>_<scenario>`
- Use `pytest.mark.asyncio` for async tests
- Mock external services (Redis, LLM, file system) with `unittest.mock`
- Use `tmp_path` fixture for file-based tests

### Frontend Tests

```bash
cd glacierkz-web

# Run all tests
npm test

# Run in watch mode
npm test -- --watch
```

**Test conventions:**
- Tests live alongside components as `*.test.tsx`
- Use React Testing Library for component tests
- Mock API calls with `jest.mock`
- Focus on user-visible behavior, not implementation details

---

## How-To Guides

### Add a New API Endpoint

1. **Define schemas** in `app/schemas/requests.py` and `app/schemas/responses.py`
2. **Create route handler** in `app/routers/` or `app/routes/`
3. **Register router** in `app/main.py` via `app.include_router(...)`
4. **Add auth dependency** if needed: `Depends(require_role(RoleLevel.analyst))`
5. **Write tests** in `tests/test_<module>.py`
6. **Update docs** in `API_REFERENCE.md`

Example:

```python
# app/routers/new_feature.py
from fastapi import APIRouter, Depends
from app.auth.rbac import require_role, RoleLevel

router = APIRouter(prefix="/api/new-feature", tags=["new-feature"])

@router.post("/action")
async def my_action(
    data: MyRequestSchema,
    _: dict = Depends(require_role(RoleLevel.analyst)),
):
    result = await do_something(data)
    return MyResponseSchema(...)
```

### Add a New Frontend Page

1. **Create page directory** at `src/app/<route>/page.tsx`
2. **Add navigation link** in `src/components/Navbar.tsx`
3. **Add translations** in `src/lib/i18n.ts` (both `ru` and `en`)
4. **Create components** in `src/components/` if needed
5. **Test the page** manually and add component tests

### Add a New ML Model

1. **Implement model class** in `glacierkz-api/app/models/`
2. **Register in model registry** (the mapping of model name → class)
3. **Update `SegmentationService`** to handle the new model type
4. **Add to MCP server** in `glacierkz-mcp/server.py` (update `get_available_models`)
5. **Write unit tests** for the model class
6. **Update `API_REFERENCE.md`** with the new model name in the predict endpoint

### Add a New MCP Tool

1. **Define the tool** in `glacierkz-mcp/server.py`
2. **Add input schema** using MCP annotations
3. **Implement the handler** with proper error handling
4. **Test with MCP Inspector** or LLM client
5. **Update `glacierkz-mcp/README.md`** with usage examples

---

## Review Checklist

Before submitting a PR, verify:

- [ ] `ruff check` passes with no errors
- [ ] `ruff format` shows no changes needed
- [ ] All existing tests pass (`pytest tests/ -v`)
- [ ] New code has corresponding tests
- [ ] API changes are reflected in `API_REFERENCE.md`
- [ ] Architecture changes are reflected in `ARCHITECTURE.md`
- [ ] No secrets, API keys, or credentials in code
- [ ] No `print()` or `console.log()` left in production code
- [ ] Error messages are clear and actionable
- [ ] Response schemas match the docs
- [ ] WebSocket messages follow the documented format
- [ ] Rate limit exemptions are justified
- [ ] New middleware is added in the correct stack order
- [ ] Frontend pages work with both `ru` and `en` locales
- [ ] Docker builds succeed (`docker compose build`)
