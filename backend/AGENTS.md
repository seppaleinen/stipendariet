## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

## Project Overview

Swedish grant assistant backend — FastAPI + PostgreSQL + pgvector. External Ollama API for LLM tasks.

## Commands

```bash
# Dev server (hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or
python main.py

# Install deps
pip install -r requirements.txt

# Lint (Trunk: black, ruff, isort, bandit, etc.)
trunk check

# Tests (pytest + pytest-asyncio, no conftest.py — run individual files)
pytest tests/test_pipeline.py
```

No `docker-compose.yml`, `pyproject.toml`, `pytest.ini`, or `conftest.py` exist.

## Architecture

- Entry point: `main.py` → `app/main.py` (FastAPI app, CORS, startup events)
- Routers: `app/api/v1/routers/` — grants, applications, profile, foundations, foundation_sync, funding, search, auth, admin
- DB layer: `app/db/` — SQLAlchemy models, session, `create_tables()` runs on startup
- Migrations: `alembic/` with 7+ versions. Alembic also runs on container startup (Dockerfile CMD).
- Foundation sync: `app/foundation/` — external API client (stiftelser.lansstyrelsen.se), APScheduler daily at 6 AM
- Pipeline: `app/pipeline/` — web discovery, extraction, validation (DuckDuckGo + Ollama)
- Workers: `app/workers/enrichment_worker.py` — Arq + Redis job queue
- Services: `app/services/` — embedding, scraping, Ollama translation
- Config: `app/core/config.py` — pydantic-settings, reads `.env`

## Env Vars (from `app/core/config.py`)

| Var | Default |
|-----|---------|
| `DATABASE_USER` | postgres |
| `DATABASE_PASSWORD` | postgres |
| `DATABASE_HOST` | localhost |
| `DATABASE_PORT` | 5432 |
| `DATABASE_NAME` | stipendariet |
| `ADMIN_USERNAME` | admin |
| `ADMIN_PASSWORD` | placeholder-password |
| `ADMIN_EMAIL` | davidbaeriksson@gmail.com |
| `JWT_SECRET_KEY` | change-me |
| `INTERNAL_AUTH_TOKEN` | internal-secret-token |
| `OLLAMA_URL` | https://ollama.labb.site |
| `OLLAMA_MODEL` | phi3:14b |
| `OLLAMA_EMBEDDING_MODEL` | nomic-embed-text |
| `REDIS_URL` | redis://dragonfly.dragonfly.svc.cluster.local:6379 |
| `BROWSERLESS_URL` | http://browserless:3000 |

## Gotchas

- **DB schema on startup**: `create_tables()` in `app/db/database.py` auto-creates tables AND alters columns at startup. This coexists with alembic migrations — be aware of potential conflicts when adding new columns.
- **pgvector**: Requires `CREATE EXTENSION IF NOT EXISTS vector` — handled in `create_tables()`.
- **Python version**: Dockerfile uses 3.13-slim. README warns 3.14 may break SQLAlchemy; 3.11–3.13 safe.
- **Tests use `@pytest.mark.asyncio`**: requires `pytest-asyncio`. No shared fixtures or conftest.
- **Backend spec**: `backend-spec.yaml` is the OpenAPI contract. `.aider.conf.json` instructs agents to follow it.
- **No docker-compose.yml** currently in repo (WARP.md references one that doesn't exist).
- **Trunk** is the linter/formatter — not ruff or black directly.
