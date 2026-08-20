# Agent Instructions: StipendieAssistenten Monorepo

## Overview
This is a monorepo containing a multi-tier application:
- **Frontend**: React/Vite application (`apps/frontend`).
- **Admin**: React/Vite admin panel (`apps/admin`).
- **Backend**: Python application (`backend/`).
- **Shared Packages**: 
  - `@stipendariet/api-client`: API client for interacting with the backend.
  - `@stipendariet/types`: Shared TypeScript interfaces/types.
  - `@stipendariet/ui`: Shared React UI components (Radix-based).

The project uses `pnpm` for package management and `turbo` (Turborepo) for task orchestration.

## Development & Commands

### Infrastructure
Requires Docker. Use these commands to manage local services (Postgres, Redis, Browserless):
- `pnpm run dev:infra`: Start infrastructure via Docker Compose.
- `pnpm run dev:stop-infra`: Stop infrastructure.
- `docker compose up -d`: Start all services defined in `docker-compose.yml`.

### Application Development
- `pnpm run dev:all`: Starts infrastructure AND all application dev servers.
- `pnpm run dev`: Runs `turbo run dev` (starts all apps).
- `pnpm run build`: Runs `turbo run build` (builds all workspace packages and apps).

### Testing
- `pnpm run test`: Runs all tests across the monorepo via Turbo.
- `pnpm run test:e2e`: Runs Playwright E2E tests (Frontend).
- `pnpm run test:all`: Runs all unit and E2E tests.
- **Unit Testing**: Uses `vitest`. To run a specific test: `pnpm --filter <package> exec vitest run <file-path>`.

## Critical Architecture & Context

### Monorepo Boundaries
- **Workspace Packages**: Use `pnpm workspace` aware commands or `turbo`.
- **Backend**: The `backend/` directory is **Python-only**. It is NOT part of the pnpm workspace. It is orchestrated via `docker-compose` and `turbo`.
- **Shared Libs**: Changes to `packages/types` or `packages/api-client` require rebuilding packages/apps to propagate type changes.

### API & Data Flow
- **Frontend** $\rightarrow$ **Backend**: Uses `@stipendariet/api-client` for communication.
- **Admin** $\rightarrow$ **Backend**: Currently uses a custom wrapper around `axios` (ref: `apps/admin/src/lib/api.ts`). **Goal: Migrate Admin to use `@stipendariet/api-client`.**
- **Authentication**: Handled via `getAuthToken()` in the client context.

### Deployment (Kubernetes)
The project uses `helmfile` for orchestration.
- Deployment uses `seppaleinen/stipendiatet` charts.
- Components: `backend`, `frontend`, `admin-frontend`.

## Developer Gotchas
- **Path Mapping**: Use `@/` aliases which resolve to `src/` within respective apps.
- **Environment Variables**: Frontend uses `import.meta.env.VITE_API_URL`. Backend/Admin use standard env vars.
- **Testing Integration**: Integration tests in `apps/frontend/src/lib/api.integration.test.ts` require the backend to be running (via Docker).
- **Build Order**: Turbo handles the dependency graph, but when manually building, ensure `@stipendariet/types` is built before `@stipendariet/api-client`.
