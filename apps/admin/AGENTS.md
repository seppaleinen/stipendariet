# Agent Instructions: Stipendiet Admin

## Overview

Admin panel for managing the enrichment pipeline, scholarship review, foundation sync, and translations. Built with React 18, TypeScript, Vite, Tailwind CSS, and Radix UI (shadcn-ui style components).

## Tech Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| **Framework** | React 18 + Vite 5 | SWC for fast refresh |
| **Type System** | TypeScript | Same relaxed config as frontend |
| **Styling** | Tailwind CSS 3.x + Radix UI | Custom components in `src/components/ui/` |
| **State** | React Query `@tanstack/react-query` | Server state |
| **Routing** | React Router DOM 6 | Protected routes via `ProtectedRoute` |
| **Auth** | JWT token in localStorage | `adminToken` key, 401 redirect to `/login` |
| **Linting** | ESLint 9 + TypeScript ESLint | Config via `@stipendariet/eslint-config` |
| **Testing** | Vitest 3.x + Testing Library | 5 test files |

## Project Structure

```
apps/admin/
├── src/
│   ├── App.tsx           # Root with routing + ProtectedRoute
│   ├── main.tsx          # Entry point
│   ├── components/
│   │   ├── ui/           # 15 Radix-based UI primitives
│   │   ├── jobs/         # Job cards (enrichment, sync, translation)
│   │   ├── AdminLayout.tsx
│   │   └── ProtectedRoute.tsx
│   ├── hooks/            # useActiveJobs, useAuth, useFoundationStats
│   ├── lib/
│   │   ├── api.ts        # Raw API client + request() wrapper
│   │   ├── auth.ts       # Token storage helpers
│   │   ├── scholarshipService.ts
│   │   └── utils.ts
│   ├── pages/
│   │   ├── DashboardPage.tsx
│   │   ├── EnrichmentResultsPage.tsx    # Enrichment pipeline UI (Phase 7)
│   │   ├── EnrichmentSourcesPage.tsx
│   │   ├── EnrichmentPromptsPage.tsx
│   │   ├── JobsPage.tsx
│   │   ├── LoginPage.tsx
│   │   ├── QueuePage.tsx
│   │   ├── ReviewPage.tsx
│   │   ├── TranslationsPage.tsx
│   │   └── types.ts
│   ├── types/
│   │   ├── index.ts
│   │   └── jobs.ts
│   └── test-setup.ts
├── vitest.config.ts
└── vite.config.ts
```

## Path Mapping

- `@/` → `./src/` (configured in `vite.config.ts` and `tsconfig.json`)

## API Client Convention

Two clients in `src/lib/api.ts`:

| Client | Use Case |
|--------|----------|
| `api` | Authenticated calls — injects `Authorization: Bearer <adminToken>` |
| `apiPublic` | Unauthenticated calls — e.g. `/auth/exchange` |

```typescript
import { api, request } from '@/lib/api';

// Preferred: request() wrapper handles 401 redirect + { data } destructuring
const { data } = await request(api.get('/admin/enrich/stats'));

// Raw client (no 401 handling, returns full response)
const response = await api.get('/admin/enrich/stats');
```

**All new code should use `request()` wrapper.** Raw `api` only for migration.

## Authentication

- Login: `POST /api/auth/exchange` (Authentik ForwardAuth → backend JWT)
- Token stored as `adminToken` in localStorage
- Auto-redirect to `/login` on 401 via `handle401()` in `request()`
- Protected routes wrapped in `<ProtectedRoute>`

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_BACKEND_URL` | `http://localhost:8000/api` | Backend API base URL |
| `VITE_API_URL` | fallback for `VITE_BACKEND_URL` | Legacy support |

## Development Commands

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Run linter
npm run lint

# Run tests
npm run test
npm run test:watch
npm run test:coverage
```

## Deployment

- Built via Dockerfile → `seppaleinen/stipendariet-admin:latest`
- Served by Nginx on `localhost:8081` (host port), `localhost:80` (container)
- Production via helmfile chart `seppaleinen/stipendiateet`

## Key Pages & Features

| Page | Component | Key Features |
|------|-----------|--------------|
| `/` | `DashboardPage.tsx` | Stats overview, quick actions |
| `/enrichment/results` | `EnrichmentResultsPage.tsx` | Pipeline results with per-field source + confidence, trace modal |
| `/enrichment/sources` | `EnrichmentSourcesPage.tsx` | Source management |
| `/enrichment/prompts` | `EnrichmentPromptsPage.tsx` | Prompt versioning UI |
| `/jobs` | `JobsPage.tsx` | Job queue monitoring (Arq/Redis) |
| `/queue` | `QueuePage.tsx` | Foundation sync queue |
| `/review` | `ReviewPage.tsx` | Scholarship approval workflow |
| `/translations` | `TranslationsPage.tsx` | Translation management |
| `/login` | `LoginPage.tsx` | Authentik ForwardAuth flow |

## Admin-Specific Patterns

### API Calls
```typescript
import { api, request } from '@/lib/api';

// Always use request() for 401 handling
const { data } = await request(api.get('/admin/enrich/field-completeness'));
```

### Error Handling
```typescript
try {
  const { data } = await request(api.post('/admin/enrich/start', { batch_size: 50 }));
} catch (error) {
  // Handled by toast in components
  console.error('Failed to start enrichment', error);
}
```

### Job Polling
```typescript
import { useActiveJobs } from '@/hooks/useActiveJobs';

const { jobs, refetch } = useActiveJobs(); // Auto-polls every 5s
```

### Foundation Stats
```typescript
import { useFoundationStats } from '@/hooks/useFoundationStats';

const { stats } = useFoundationStats(); // Cached, refetches on demand
```

## Type Conventions

- **snake_case** in API responses (backend)
- **camelCase** in frontend types
- Shared types from `@stipendariet/types` (workspace package)
- Local types in `src/types/` or page-level `types.ts`

## Testing Conventions

- Tests live alongside code: `Page.test.tsx`, `hook.test.tsx`
- Use Vitest with jsdom
- Mock `api` and `request` via `vi.mock('@/lib/api')`
- Test files use `files: ["**/*.test.{ts,tsx}"]` override in `eslint.config.js`

## Enrichment Pipeline v2 (Phase 7) — Admin UI

`EnrichmentResultsPage.tsx` displays:
- **Per-field source URLs** (Globe icons) — which source contributed each field
- **Per-field confidence scores** — LLM-assigned confidence (0.0-1.0)
- **View Trace modal** — Full pipeline execution including re-search iterations
- **Export** — CSV/JSON with filters

Data comes from new endpoints:
- `GET /api/admin/enrich/field-completeness`
- `GET /api/admin/enrich/prompt-metrics`
- `POST /api/admin/enrich/export`

## Agent Guidelines

- **Before implementing**: Check ADRs in `/docs/adr/` (especially 0012 for enrichment pipeline)
- **For new components**: Use Radix primitives in `src/components/ui/`
- **For new pages**: Add route in `App.tsx`, nav entry in `AdminLayout.tsx`
- **Lint before PR**: `npm run lint` must pass (shared eslint config)
- **Tests required**: Add tests for new data hooks or business logic
- **No console.log in production**: Use sonner toasts for user-facing errors
- **401 handling**: Always use `request()` wrapper — never raw `api` for protected endpoints

---

## References

- [README.md](./README.md) — Quick start
- [WARP.md](./WARP.md) — Full project overview for Warp.dev (note: docker port 8081)
- [CONTEXT.md](../../CONTEXT.md) — Domain language and concepts
- `docs/adr/0012-enrichment-pipeline-v2-architecture.md` — Pipeline v2 architecture
- `docs/enrichment-pipeline.md` — Admin user guide
- `backend/AGENTS.md` — Backend agent conventions
- `apps/frontend/AGENTS.md` — Frontend agent conventions