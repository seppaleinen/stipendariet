# StipendieAssistenten

A Swedish grant discovery and assistance platform that helps families find scholarships and stipends whose purpose matches their personal situation.

## Overview

**StipendieAssistenten** consists of three main applications:

| Application | Purpose | URL |
|-------------|---------|-----|
| **Frontend** | User-facing grant discovery and application generation | http://localhost:8082 |
| **Admin Panel** | Enrichment pipeline management, review workflow | http://localhost:8081 |
| **Backend API** | FastAPI service with PostgreSQL + pgvector | http://localhost:8000 |

## Quick Start

### Prerequisites

- **Node.js 22+** and **pnpm** (monorepo package manager)
- **Docker** (for local infrastructure services)
- **Python 3.13** (backend development)

### Development Setup

```bash
# 1. Clone the repository
git clone <REPO_URL>
cd stipendariet

# 2. Install dependencies
pnpm install

# 3. Start infrastructure (PostgreSQL, Redis, SearXNG)
pnpm run dev:infra

# 4. Start applications
pnpm run dev

# Open in browser:
# - Frontend: http://localhost:8082
# - Admin: http://localhost:5173 (auth via Authentik)
# - Backend API: http://localhost:8000/docs (Swagger UI)
```

### Full Stack with Docker

```bash
# Start all services (requires Docker)
docker compose up -d

# Available services:
# - Frontend: port 8082
# - Admin: port 8081  
# - Backend: port 8000
# - SearXNG: port 8080
# - PostgreSQL: port 5432
# - Redis: port 6379
```

## Project Structure

```
stipendariet/
├── apps/
│   ├── frontend/          # User-facing React/Vite app
│   └── admin/             # Admin panel (pipeline management)
├── backend/               # FastAPI backend (Python)
├── packages/
│   ├── api-client/        # Shared API client
│   ├── types/             # Shared TypeScript types
│   └── ui/                # Shared Radix UI components
├── docs/
│   ├── architecture-overview.md  # System diagrams
│   ├── enrichment-pipeline.md  # Admin user guide
│   └── adr/                    # Architectural decisions
└── .githooks/             # Pre-push lint hooks
```

## Available Scripts

### Monorepo (Turbo)

```bash
pnpm run dev          # Start all development servers
pnpm run build        # Build all packages and apps
pnpm run lint         # Run linters
pnpm run test         # Run all tests
pnpm run test:all     # Run all tests + E2E
```

### Individual Apps

```bash
# Frontend
cd apps/frontend
npm run dev           # Vite dev server
npm run test          # Run unit tests
npm run test:e2e      # Run Playwright E2E

# Admin  
cd apps/admin
npm run dev           # Vite dev server
npm run test          # Run unit tests

# Backend
cd backend
uvicorn app.main:app --reload  # FastAPI with hot reload
pytest tests/         # Run pytest
trunk check           # Lint with trunk
```

## Architecture

The system uses a **unified grant model** where both traditional grants and Swedish foundations are normalized to a common schema. Key components:

- **Frontend**: React + Vite + TailwindCSS, consumes REST API
- **Backend**: FastAPI + PostgreSQL + pgvector, serves unified `/funding` endpoint
- **Enrichment Pipeline**: Multi-stage LLM-powered pipeline for foundation data extraction
  - Stage 0: Bolagsverket registry lookup (authoritative founder website)
  - Stage 1: SearXNG multi-engine web search (DDG fallback)
  - Stages 2-7: Validation, crawling, extraction, merge, re-search, service area

See **[docs/architecture-overview.md](./docs/architecture-overview.md)** for detailed diagrams.

## Key Features

- **Grant Discovery**: Search and filter grants by category, location, eligibility
- **AI Application Generation**: Generate application drafts using LLMs
- **Profile Matching**: Family profiles match against foundation purposes using embeddings
- **Foundation Enrichment**: Admin pipeline extracts structured data from foundation websites

## Testing

| Tier | Framework | Location |
|------|-----------|----------|
| Frontend Unit | Vitest + Testing Library | `apps/frontend/src/**/*.test.{ts,tsx}` |
| Admin Unit | Vitest + Testing Library | `apps/admin/src/**/*.test.tsx` |
| Backend Unit | pytest + pytest-asyncio | `backend/tests/` |
| E2E | Playwright | `apps/frontend/e2e/` |

```bash
pnpm run test              # All unit tests
pnpm run test:e2e          # E2E tests only
pnpm run test:coverage     # With coverage report
```

## Deployment

Production deployment uses **Kubernetes + helmfile** with the `seppaleinen/stipendiateet` charts:

- **frontend**: `seppaleinen/stipendariet-frontend:latest`
- **admin**: `seppaleinen/stipendariet-admin:latest`  
- **backend**: `seppaleinen/stipendariet-backend:latest`

## Documentation

- **[AGENTS.md](./AGENTS.md)** - Agent pipeline rules, tooling conventions
- **[CONTEXT.md](./CONTEXT.md)** - Domain language and relationships
- **[TESTING.md](./TESTING.md)** - Test architecture and running tests
- **docs/architecture-overview.md** - System diagrams and tech stack
- **docs/enrichment-pipeline.md** - Admin user guide for pipeline
- **docs/adr/** - Architectural decision records

## ADR Index

| # | Title | Status |
|---|-------|--------|
| 0001 | Alembic Migration Gating | Accepted |
| 0002 | Migrations Check No-Driver Test | Accepted |
| 0003 | Admin Auth via Authentik ForwardAuth | Accepted |
| 0004 | Backend Model Separation | Accepted |
| 0005 | Frontend Grants Feature Extraction | Accepted |
| 0006 | Admin Types Consolidation | Accepted |
| 0007 | Deduplicate OpenAPI Tags | Accepted |
| 0008 | Pipeline Service Abstraction | Accepted |
| 0009 | Phase 0 Enrichment Pipeline Infrastructure | Accepted |
| 0010 | Bolagsverket Registry Lookup | Accepted |
| 0011 | SearXNG Multi-Engine Search | Accepted |
| 0012 | Enrichment Pipeline v2 Architecture | Accepted |

## License

See [LICENSE](./LICENSE) file.

## Contributing

1. Read [AGENTS.md](./AGENTS.md) for agent development conventions
2. Check ADRs in `docs/adr/` before making architectural changes
3. Run `pnpm run lint` before committing
4. Ensure backend tests pass: `cd backend && pytest -v`