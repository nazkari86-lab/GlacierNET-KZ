---
name: glaciernet-kz-dev
description: >
  GlacierNET-KZ glacier ML monorepo — src/ training, glacierkz-api FastAPI, glacierkz-web Next.js.
  Use for geospatial ML, API, dashboard, auth in ~/Downloads/GlacierNET-KZ.
---

# GlacierNET-KZ — Dev Skill

## Verify

```bash
cd /Users/dulatnurlanuly/Downloads/GlacierNET-KZ
pytest -q
```

API smoke: `cd glacierkz-api && python -c "from app.main import app; print(app.title)"`

## Scope slices

| Slice | Path |
|-------|------|
| Train / model | `src/` one module |
| API endpoint | `glacierkz-api/app/routers/` |
| Auth | `glacierkz-api/app/auth/`, `middleware/admin_auth.py` |
| UI | `glacierkz-web/src/` |

## Caution

- **Never** load GeoTIFF/raster into chat
- `data/` and `results/` are large — grep JSON/CSV summaries
- Science claims must match `docs/` and `results/`

## Agents

- `code-explorer` → `code-archaeologist` on first visit
- `security-team` for auth changes
- `stack-specialist` for PyTorch `src/`
