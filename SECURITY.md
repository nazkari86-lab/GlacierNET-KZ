# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | -------------------- |
| 0.1.x   | :white_check_mark:   |

## Reporting a Vulnerability

**Please do not open public GitHub issues for security vulnerabilities.**

Instead, email the maintainers or open a private security advisory on GitHub:

1. Go to **Security → Advisories → Report a vulnerability**
2. Describe the issue, affected components, and reproduction steps
3. We aim to acknowledge within 48 hours

## Scope

This policy covers:

- `glacierkz-api/` — FastAPI backend, authentication, file upload
- `glacierkz-web/` — Next.js frontend
- `src/` — ML inference pipeline
- Docker images and CI/CD workflows

## Known Security Practices

- API keys and secrets must be set via environment variables (see `.env.example`)
- Never commit `.env`, `client_secret.json`, or model credentials
- `MAX_FILE_SIZE_MB` limits upload size (default 200 MB)
- Rate limiting: 120 req/min, 5000 req/hour
- Admin routes require authentication (`AdminAuthMiddleware`)
- CORS origins configured via `CORS_ORIGINS` env var

## Dependency Scanning

CI runs `bandit` (Python SAST) and `safety` (dependency CVE check) on every push.
Run locally:

```bash
bandit -r glacierkz-api/app/ -ll --skip B101
safety check -r requirements.txt -r glacierkz-api/requirements-api.txt
```
