# Agent Instructions: Stipendiet Frontend

## Overview

**Stipendium Assistenten** is a React-based web application that helps Swedish families discover and apply for grants and scholarships. Built with Vite, TypeScript, React, shadcn-ui, and Tailwind CSS, it connects to a FastAPI backend.

## Tech Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| **Framework** | React 18 + Vite 5 | SWC for fast refresh |
| **Type System** | TypeScript | Relaxed: `noImplicitAny: false`, `strictNullChecks: false` |
| **Styling** | Tailwind CSS 3.x + shadcn-ui | Radix UI primitives, custom slate theme |
| **State** | React Query `@tanstack/react-query` | Server state caching |
| **Routing** | React Router DOM 6 | Client-side routing |
| **Linting** | ESLint 9 + TypeScript ESLint | Config via `@stipendariet/eslint-config` |
| **Testing** | Vitest 3.x + Testing Library | 7 test files (~15 tests) |

## Project Structure

```
apps/frontend/
├── src/
│   ├── App.tsx           # Root component with routing
│   ├── main.tsx          # Entry point
│   ├── components/       # Reusable UI (Layout, FAQSchema, etc.)
│   ├── features/         # Domain-specific modules (grants, profile)
│   ├── hooks/            # Custom hooks (use-toast)
│   ├── lib/              # Utilities (api.ts, utils.ts)
│   ├── pages/            # Route components
│   ├── contexts/         # React contexts (Auth, Profile, SSR)
│   ├── types/            # TypeScript definitions
│   └── data/             # Static data (swedish-regions.ts)
├── e2e/                  # Playwright E2E tests
├── public/config.js      # Runtime config for Vite
└── vite.config.ts        # Vite config with `@/` alias
```

## Path Mapping

- `@/` → `./src/` (configured in `vite.config.ts` and `tsconfig.json`)
- Use path aliases consistently — never relative imports crossing src/

## API Client Convention

- **All API calls go through `src/lib/api.ts`**
- Uses `@stipendariet/api-client` for HTTP layer
- Transforms snake_case backend responses to camelCase frontend types
- Falls back to mock data when backend unavailable

```typescript
// Correct
import { getGrants } from '@/lib/api';

// Wrong — bypass API client
import { api } from '@/lib/api';  // Only if you need raw client
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_URL` | `/api` | Backend API base URL |

Access via `import.meta.env.VITE_API_URL`. Prefix **must** be `VITE_` for Vite to expose.

## Development Commands

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:8080, redirected to 8082 per docker-compose)
npm run dev

# Build for production
npm run build

# Run linter
npm run lint

# Run tests
npm run test
npm run test:watch  # for TDD
```

## Deployment

- Built via Dockerfile → `seppaleinen/stipendariet-frontend:latest`
- Served by Nginx on `localhost:8082` (host port), `localhost:8080` (container)
- Production uses helmfile chart `seppaleinen/stipendiateet`

## Key Pages & Components

| Page | Component | Key Features |
|------|-----------|--------------|
| `/` | `Home.tsx` | Overview, feature highlights |
| `/grants` | `Grants.tsx` | Filterable grant list with search |
| `/grants/[id]` | `GrantDetail.tsx` | Individual grant view |
| `/applications` | `Applications.tsx` | Saved/Submitted applications |
| `/generate` | `Generate.tsx` | AI application generation |
| `/family-setup` | `FamilySetup.tsx` | Profile configuration |
| `/matching` | `Matching.tsx` | Foundation matching results |

## Type Conventions

- **snake_case** in API responses (backend)
- **camelCase** in frontend types
- Transformation handled in `api.ts` mappers
- Never use `any` — prefer `unknown` + type guards

## Testing Conventions

- Tests live alongside code: `Component.test.tsx`, `utils.test.ts`
- Use Vitest with jsdom test environment
- Mock API calls via `vi.mock('@/lib/api')`
- Integration tests in `api.integration.test.ts` require running backend

## Common Patterns

### API Usage
```typescript
import { getGrants } from '@/lib/api';

const { data } = useQuery(['grants'], () => getGrants({ category: 'education' }));
```

### Type Safety
```typescript
// Use Zod schemas for runtime validation
import { grantSchema } from '@/types/grants';

const validated = grantSchema.safeParse(apiResponse);
```

### Error Handling
```typescript
const { error } = useQuery(...);
// error is typed by the API client
```

## Agent Guidelines

- **Before implementing**: Check ADRs in `/docs/adr/` for architectural decisions
- **For new components**: Use shadcn/ui primitives when possible
- **For new pages**: Register route in `App.tsx`, add nav item in Layout
- **Lint before PR**: `npm run lint` must pass
- **Tests required**: Add tests for new data transformation or business logic
- **No console.log in production**: Use the toast system or proper error boundaries

---

## References

- [WARP.md](./WARP.md) — Full project overview for Warp.dev
- [CONTEXT.md](../../CONTEXT.md) — Domain language and concepts
- `backend/AGENTS.md` — Backend agent conventions