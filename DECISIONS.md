# GlacierNET-KZ — Decisions

---

## 2026-07-01 — ASTRAFORGE project layer

**Decision:** Local CLAUDE.md + `glaciernet-kz-dev` skill.

---

## 2026-06 — Monorepo: src + API + web

**Decision:** Three deployable surfaces share one repo; API orchestrates training/results, web is client.

**Reversibility:** Hard to split later.

---

## 2026-06 — FastAPI middleware stack

**Decision:** Layered middleware in `main.py`: CORS, rate limit, cache, security headers, admin auth, request logging.

**Files:** `glacierkz-api/app/middleware/`

---

## 2026-06 — U-Net as primary segmentation model

**Decision:** U-Net on real Sentinel-2/Landsat pipeline; results in `results/` (F1≈0.876 documented in README).

**Reversibility:** Medium — retraining cost.

---

## 2026-06 — RBAC for admin routes

**Decision:** `app/auth/rbac.py` + `admin_auth` middleware for privileged operations.

**Reversibility:** Hard — security sensitive.
