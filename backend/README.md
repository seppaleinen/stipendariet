# StipendieAssistenten Backend

FastAPI backend for grant discovery, profile management, and foundation enrichment. Uses PostgreSQL with pgvector for semantic search, Redis for job queues, and external Ollama API for LLM operations.

## Overview

**Swedish grant assistant backend** — FastAPI + PostgreSQL + pgvector. External Ollama API for LLM tasks.

The backend serves:
- **Unified Funding API**: Combines grants and foundations into a single endpoint
- **Profile Matching**: Family profiles matched against foundation purposes
- **Enrichment Pipeline**: Multi-stage LLM extraction for foundation data
- **Job Queue**: Arq + Redis for async processing

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | FastAPI + uvicorn |
| Database | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Queue | Arq (Redis) |
| LLM | LiteLLM proxy + Ollama |
| Search | SQL full-text + pgvector embeddings |

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, startup events
│   ├── api/
│   │   ├── v1/routers/    # API endpoints (grants, applications, etc.)
│   │   └── admin/         # Admin-only endpoints
│   ├── db/
│   │   ├── database.py    # SQLAlchemy engine, connection retry
│   │   ├── models/        # Entity-specific ORM models
│   │   └── schemas.py     # Pydantic request/response models
│   ├── crud/              # Data access layer
│   ├── pipeline/          # Enrichment pipeline stages
│   ├── services/          # Business logic (scraping, LLM, etc.)
│   ├── workers/           # Arq job queue workers
│   ├── repositories/      # Repository pattern abstraction
│   └── core/              # Config, security, utilities
├── tests/                 # Integration and unit tests
├── alembic/               # Database migrations
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Build config, pytest settings
├── Dockerfile             # Container build
└── docker-compose.yml     # Local services (postgres, redis, searxng)
```

## Quick Start

### Local Development

```bash
# Using uvicorn (hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or the entrypoint script
python main.py

# With Docker (requires Docker)
docker compose up -d postgres redis
uvicorn app.main:app --reload
```

### Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Or using uv (recommended)
uv pip install -r requirements.txt
```

### Run Linter

```bash
# Using trunk (as configured)
trunk check

# Or ruff directly
ruff check .
```

## Running Tests

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_pipeline.py -v

# Run with asyncio markers
pytest tests/test_routers.py::test_get_funding -v

# Tests use @pytest.mark.asyncio for async tests
# No shared conftest.py - tests are run individually
```

## Database

### Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# View current revision
alembic current
```

### Connection

The database creates tables on startup via `create_tables()`. This coexists with Alembic migrations — be aware of potential conflicts when adding new columns.

```
Default connection (from .env):
  User: postgres
  Password: postgres
  Host: localhost
  Port: 5432
  Database: stipendariet
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost/stipendariet` | Full connection string |
| `DATABASE_HOST` | localhost | Database host |
| `DATABASE_PORT` | 5432 | Database port |
| `DATABASE_USER` | postgres | Database user |
| `DATABASE_PASSWORD` | postgres | Database password |
| `DATABASE_NAME` | stipendariet | Database name |
| `POSTGRES_DB` | stipendariet | Docker compose |
| `POSTGRES_USER` | postgres | Docker compose |
| `POSTGRES_PASSWORD` | postgres | Docker compose |
| `SECRET_KEY` | (generated) | JWT signing key |
| `ADMIN_EMAIL` | (required) | Admin user email |
| `ADMIN_PASSWORD` | (required in prod) | Admin password |
| `JWT_SECRET_KEY` | (required) | JWT secret |
| `INTERNAL_AUTH_TOKEN` | (required) | ForwardAuth validation |
| `LITELLM_URL` | http://localhost:4000 | LiteLLM proxy |
| `LITELLM_TEXT_MODEL` | gemma-4-12b | Default LLM |
| `LITELLM_EMBEDDING_MODEL` | nomic-embed-text | Embedding model |
| `SEARXNG_URL` | http://localhost:8080 | Search engine |
| `BOLAGSVERKET_URL` | https://data.bolagsverket.se | Foundation registry |
| `BROWSERLESS_URL` | http://localhost:3000 | Playwright rendering |

## API Endpoints

### Public Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/grants/` | List grants |
| POST | `/api/grants/` | Create grant |
| GET | `/api/grants/{id}` | Get grant |
| POST | `/api/applications/` | Submit application |
| GET | `/api/funding/` | Unified funding (grants + foundations) |
| GET | `/api/search/foundations` | Vector search |
| POST | `/api/profile/` | Save profile |
| GET | `/api/profile/` | Get profile |

### Admin Endpoints (requires JWT)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/admin/enrich/details` | Enrichment results |
| POST | `/api/admin/enrich/start` | Start enrichment |
| GET | `/api/admin/enrich/status` | Status summary |
| GET | `/api/admin/enrich/trace/{id}` | Pipeline trace |
| GET | `/api/admin/enrich/field-completeness` | Metrics dashboard |
| POST | `/api/admin/enrich/export` | Export data |
| POST | `/api/auth/exchange` | Authentik ForwardAuth exchange |

## The Enrichment Pipeline

### Architecture

7-stage pipeline for extracting structured data from foundation websites:

| Stage | Purpose | Implementation |
|-------|---------|----------------|
| 0 | Bolagsverket registry lookup | Check official website URL |
| 1 | Multi-engine search (SearXNG) | Find candidate URLs |
| 2 | Validation | LLM + heuristics verify relevance |
| 3 | Crawl | Trafilatura → Playwright fallback |
| 4 | Extract | Per-source LLM extraction |
| 5 | Merge | Highest-confidence-wins |
| 6 | Re-search | Targeted queries for missing fields |
| 7 | Service Area | Geographic extraction |

See **docs/architecture-overview.md** for flow diagrams.

## Key Concepts

- **Foundation**: Swedish nonprofit organization from Bolagsverket registry
- **Profile**: User's family situation (structured + self-description)
- **Match**: Foundation paired with similarity score against profile
- **Service Area**: Geographic eligibility (county/municipality code)

## Security

- **Environment variables**: Never hardcode secrets
- **JWT**: HS256 for admin tokens
- **ForwardAuth**: Authentik validates admin requests
- **Rate limiting**: API clients have configurable limits

## Debug & Inspection

```bash
# View database
docker exec -it postgres psql -U postgres -d stipendariet

# Test seed data
python create_admin_user.py

# Inspect migrations
alembic history
```

## Git Hooks

```bash
# Activate pre-push hook (runs ruff check on backend/)
git config core.hooksPath .githooks
```

## Related Documentation

- **[Root README.md](../README.md)** - Monorepo overview
- **[CONTEXT.md](../CONTEXT.md)** - Domain language
- **[AGENTS.md](../AGENTS.md)** - Agent conventions
- **docs/architecture-overview.md** - System diagrams
- **docs/enrichment-pipeline.md** - Admin user guide
- **docs/adr/** - Architectural decisions