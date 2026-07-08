# GlacierNET-KZ — Project Rules

ML-мониторинг отступания ледников Казахстана: U-Net, Sentinel-2/Landsat, API + web dashboard.

Path: `/Users/dulatnurlanuly/Downloads/GlacierNET-KZ`

## Entry points

| What | Path |
|------|------|
| ML pipeline | `src/` (`train.py`, `config.py`, `data_loader.py`, …) |
| FastAPI backend | `glacierkz-api/app/main.py` |
| Next.js frontend | `glacierkz-web/` |
| MCP server | `glacierkz-mcp/` |
| Docs | `docs/`, `README.md` |
| Results | `results/` (trained metrics, tables) |

## Commands

```bash
cd /Users/dulatnurlanuly/Downloads/GlacierNET-KZ

# Tests
pytest -q

# API (typical)
cd glacierkz-api && uvicorn app.main:app --reload

# Web
cd glacierkz-web && npm run dev
```

Activate project venv if present: `source .venv/bin/activate`

## Module map (edit scope carefully)

| Area | Path | Notes |
|------|------|-------|
| Training / ML | `src/` | Many modules — one slice at a time |
| API | `glacierkz-api/app/` | Routers, middleware, auth |
| Web | `glacierkz-web/` | Next.js dashboard |
| Data | `data/` | GeoTIFF, large — never read into context |
| Notebooks | `notebooks/` | Research / repro |
| Research write-up | `paper/` | methodology and results notes |

## Boundaries

1. **`data/` and `results/`** — path references only; files are huge
2. **Auth/RBAC** — `glacierkz-api/app/auth/`, `middleware/admin_auth.py` → careful changes
3. Do not break reproducibility docs (`docs/REPRODUCIBILITY.md`)
4. Multiple venvs (`.venv`, `.venv-tf`) — use project's documented one
5. `experimental/` — clearly mark if promoting to `src/`

## ASTRAFORGE workflow

```
/you в glaciernet-kz: <задача>
```

| Task | Agent |
|------|-------|
| ML model | `stack-specialist` (pytorch) + scope `src/` |
| API | `code-creator` + scope `glacierkz-api/` |
| Frontend | scope `glacierkz-web/` |
| Security | `security-team` for auth middleware |
| Explore | `code-explorer` → `code-archaeologist` |

## Current focus

- [ ] API auth/RBAC hardening
- [ ] Training router (`glacierkz-api/app/routers/training.py`)
- [ ] Web hub dashboard stability

## Definition of Done

1. `pytest -q` PASS (or scoped test module)
2. API starts without import errors if API touched
3. DECISIONS.md for auth/architecture changes

## Language

- User: Russian | Code/commits: English
