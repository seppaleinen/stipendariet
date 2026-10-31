# StipendieAssistenten - Admin Panel

Admin interface for managing the enrichment pipeline, reviewing scholarships, and syncing foundation data. Uses React 18, TypeScript, Vite, Tailwind CSS, and Radix UI primitives.

## Overview

The admin panel provides:
- **Foundation Enrichment**: Multi-stage LLM-powered pipeline for extracting structured data
- **Job Monitoring**: Track enrichment jobs via Arq + Redis queue
- **Prompt Management**: Version control for LLM extraction prompts
- **Translation Management**: Manage multilingual foundation descriptions
- **Review Workflow**: Approve and curate foundation data

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | React 18 + Vite 5 (SWC) |
| Type System | TypeScript (relaxed config) |
| Styling | Tailwind CSS 3.x + Radix UI |
| State | React Query `@tanstack/react-query` |
| Routing | React Router DOM 6 |
| Auth | JWT via Authentik ForwardAuth |
| Linting | ESLint 9 + TypeScript ESLint |
| Testing | Vitest 3.x |

## Project Structure

```
apps/admin/
├── src/
│   ├── App.tsx           # Root with routing + ProtectedRoute
│   ├── main.tsx          # Entry point
│   ├── components/
│   │   ├── ui/           # Radix-based UI primitives
│   │   ├── jobs/         # Job monitoring cards
│   │   ├── AdminLayout.tsx
│   │   └── ProtectedRoute.tsx
│   ├── hooks/            # Custom hooks (useAuth, useActiveJobs, useFoundationStats)
│   ├── lib/
│   │   ├── api.ts        # API client (api + request wrapper)
│   │   ├── auth.ts       # Token storage
│   │   └── scholarshipService.ts
│   ├── pages/
│   │   ├── DashboardPage.tsx
│   │   ├── EnrichmentResultsPage.tsx
│   │   ├── EnrichmentSourcesPage.tsx
│   │   ├── EnrichmentPromptsPage.tsx
│   │   ├── JobsPage.tsx
│   │   ├── QueuePage.tsx
│   │   ├── ReviewPage.tsx
│   │   ├── TranslationsPage.tsx
│   │   └── LoginPage.tsx
│   └── test-setup.ts
├── vitest.config.ts
└── vite.config.ts
```

## Quick Start

```bash
# Install dependencies
npm install

# Start development server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Run linter
npm run lint

# Run tests
npm run test
npm run test:coverage
```

## Authentication

The admin panel uses **Authentik ForwardAuth** for authentication:

1. Unauthenticated requests to `/admin/*` redirect to Authentik login
2. After successful login, Authentik injects headers:
   - `X-Forwarded-Email`
   - `X-Forwarded-User`
   - `X-Forwarded-Groups`
3. Backend exchanges these for a JWT via `POST /api/auth/exchange`
4. JWT stored as `adminToken` in localStorage
5. All subsequent requests include `Authorization: Bearer <token>`

### API Client Convention

Two clients in `src/lib/api.ts`:

| Client | Use Case |
|--------|----------|
| `api` | Raw HTTP client (migration use only) |
| `request()` | Wrapper with 401 redirect + `{ data }` destructuring |

```typescript
import { api, request } from '@/lib/api';

// Preferred: handles 401 redirect, returns { data }
const { data } = await request(api.get('/admin/enrich/stats'));

// Raw client (no 401 handling, returns full response)
const response = await api.get('/admin/enrich/stats');
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_BACKEND_URL` | `http://localhost:8000/api` | Backend API URL |
| `VITE_API_URL` | fallback for `VITE_BACKEND_URL` | Legacy support |

## Key Features

### Enrichment Pipeline (Phase 7)

`EnrichmentResultsPage.tsx` displays per-foundation enrichment status:

| Status | Description |
|--------|-------------|
| COMPLETED | Successfully enriched (≥5 fields) |
| FAILED | Pipeline failed after retries |
| NO_DATA | No fields extracted |
| NO_VALID_SITE | No valid website found |
| PROCESSING | Currently running |
| PENDING | Queued, not yet started |

**Per-field observability:**
- Source URLs (which website provided each field)
- Confidence scores (0.0–1.0)
- Full trace modal showing pipeline execution

### Job Queue Monitoring

`useActiveJobs()` hook polls job status every 5 seconds from Redis (Arq).

### Prompt Versioning

`EnrichmentPromptsPage.tsx` manages LLM extraction prompts with:
- Semantic versioning
- A/B testing capabilities
- Production vs. testing version selection
- Metrics: confidence, field completeness, run count

## Testing

```bash
# Run tests
npm run test

# With coverage
npm run test:coverage

# Run specific test file
npx vitest run src/pages/LoginPage.test.tsx
```

Tests live alongside code with vitest + jsdom. Mock API calls via `vi.mock('@/lib/api')`.

## Deployment

- **Docker image**: `seppaleinen/stipendariet-admin:latest`
- **Served by**: Nginx on port 80 (container)
- **Host port**: 8081
- **Helm chart**: `seppaleinen/stipendiateet` via helmfile

## Pipeline Configuration

The enrichment pipeline is configured via environment variables:

| Variable | Purpose |
|----------|---------|
| `SEARXNG_URL` | Search engine URL |
| `JWT_SECRET_KEY` | JWT signing key |
| `INTERNAL_AUTH_TOKEN` | ForwardAuth validation |
| `LITELLM_URL` | LLM proxy |
| `OLLAMA_URL` | Ollama API endpoint |

## Git Hooks

Same as root repo - activates pre-push lint check.

## Related Documentation

- **[Root README.md](../README.md)** - Monorepo overview
- **[CONTEXT.md](../CONTEXT.md)** - Domain language
- **[AGENTS.md](../AGENTS.md)** - Agent conventions
- **docs/enrichment-pipeline.md** - Admin user guide
- **docs/adr/0012-enrichment-pipeline-v2-architecture.md** - Pipeline design