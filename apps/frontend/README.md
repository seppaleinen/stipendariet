# StipendieAssistenten - Frontend

A React-based web application that helps Swedish families discover grants and scholarships. Users describe their situation once and receive matched foundations whose purposes align with their needs.

## Overview

Built with **Vite 5**, **TypeScript**, **React 18**, **shadcn-ui**, and **Tailwind CSS**. Connects to a FastAPI backend for grant discovery, profile management, and AI-powered application generation.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | React 18 + Vite 5 (SWC) |
| Type System | TypeScript (relaxed: `noImplicitAny: false`) |
| Styling | Tailwind CSS 3.x + shadcn-ui (Radix primitives) |
| State | React Query `@tanstack/react-query` |
| Routing | React Router DOM 6 |
| Linting | ESLint 9 + TypeScript ESLint |
| Testing | Vitest 3.x + Playwright |

## Project Structure

```
apps/frontend/
├── src/
│   ├── App.tsx           # Root component with routing
│   ├── main.tsx          # Entry point
│   ├── components/       # Reuseable UI components
│   ├── features/         # Domain-specific modules (grants, profile)
│   ├── hooks/            # Custom hooks (use-toast, use-mobile)
│   ├── lib/              # Utilities, API client
│   ├── pages/            # Route components
│   ├── contexts/         # React contexts (Auth, Profile, SSR)
│   ├── types/            # TypeScript definitions
│   └── data/             # Static data (swedish-regions.ts)
├── e2e/                  # Playwright end-to-end tests
├── public/               # Static assets
└── vite.config.ts        # Vite config with `@/` alias
```

## Quick Start

```bash
# Install dependencies
npm install

# Start development server (http://localhost:8082)
npm run dev

# Build for production
npm run build

# Run linter
npm run lint

# Run tests
npm run test
npm run test:watch  # for TDD
npm run test:e2e    # end-to-end tests
```

### Docker Development

```bash
# From repo root - start full stack with Docker
cd ../..
docker compose -f docker-compose.yml up -d

# Or using Turbo with Docker infrastructure
pnpm run dev:infra    # Start Postgres, Redis, SearXNG
pnpm run dev          # Start frontend dev server
```

## Path Mapping

- `@/` → `./src/` (configured in `vite.config.ts` and `tsconfig.json`)
- Always use path aliases — never relative imports crossing src/

## API Client Convention

All API calls go through `src/lib/api.ts`:

```typescript
import { getGrants, getProfile } from '@/lib/api';

// Server state with caching
const { data } = useQuery(['grants'], () => getGrants({ category: 'education' }));

// API client handles:
// - snake_case → camelCase transformation
// - Mock data fallback when backend unavailable
// - Authentication via @tanstack/react-query
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_URL` | `/api` | Backend API base URL |

Access via `import.meta.env.VITE_API_URL`. Prefix **must** be `VITE_` for Vite to expose.

## Key Pages

| Path | Component | Purpose |
|------|-----------|---------|
| `/` | `Home.tsx` | Overview, grant highlights |
| `/grants` | `Grants.tsx` | Filterable grant list with search |
| `/grants/[id]` | `GrantDetail.tsx` | Individual grant view |
| `/applications` | `Applications.tsx` | Saved/submitted applications |
| `/generate` | `Generate.tsx` | AI application generation |
| `/family-setup` | `FamilySetup.tsx` | Profile configuration |
| `/matching` | `Matching.tsx` | Foundation matching results |

## Testing

### Unit Tests

```bash
npm run test              # Run all tests
npm run test:watch        # Watch mode for TDD
npm run test:coverage     # With coverage report
```

### End-to-End Tests

```bash
npm run test:e2e          # Run Playwright tests
npm run test:e2e:ui       # Interactive mode
npm run test:e2e:debug    # Debug mode
```

Tests live alongside code: `Component.test.tsx`, `utils.test.ts`. Integration tests in `api.integration.test.ts` require running backend via Docker.

## Deployment

- **Docker image**: `seppaleinen/stipendariet-frontend:latest`
- **Served by**: Nginx on port 8080 (container)
- **Host port**: 8082 (to avoid conflict with SearXNG)
- **Helm chart**: `seppaleinen/stipendiateet` via helmfile

## Type Conventions

- Backend uses **snake_case** in API responses
- Frontend uses **camelCase** in types
- Transformation handled in `api.ts` mappers
- Prefer `unknown` + type guards over `any`

## Git Hooks

Activate pre-push lint hook:

```bash
git config core.hooksPath .githooks
```

Pre-push runs `ruff check .` on backend and blocks on lint errors.

## Related Documentation

- **[Root README.md](../README.md)** - Monorepo overview
- **[CONTEXT.md](../CONTEXT.md)** - Domain language
- **[AGENTS.md](../AGENTS.md)** - Agent conventions
- **docs/architecture-overview.md** - System diagrams