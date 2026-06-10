# Monorepo Migration Plan

## Goal

Migrate all subrepos (frontend, admin, backend) into a single monorepo using pnpm workspaces and Turbo with backend integrated into the pipeline via Docker.

## Repository

- **Test repo**: `git@github.com:seppaleinen/stipendariet.git`
- **Local path**: `~/workspace/personal/stipendariet/stipendariet/`
- Existing repos stay untouched — this is an experiment to test the monorepo approach before committing

---

## Phase 1: Foundation ✅ COMPLETE

Scaffold the monorepo structure with pnpm workspaces + Turbo.

| Task | Status | Notes |
|------|--------|-------|
| Root `package.json` (pnpm, turbo) | Done | pnpm v10.5.0, turbo v2.9.16 |
| `pnpm-workspace.yaml` | Done | `apps/*`, `packages/*`; backend excluded (no npm deps) |
| `turbo.json` | Done | build/dev/lint/test pipelines; `@backend/build` bridge via docker compose |
| `tsconfig.base.json` | Done | Bundler resolution, JSX react-jsx, strict mode + path aliases for ui/types |
| Root `.gitignore`, `.env.example` | Done | Runtime data dir anchored to `/data/` only (not nested `src/data/`) |
| Docker compose setup | Done | Monorepo-pathed services for dev/prod |

**Result**: 22 files scaffolded, pushed and CI running.

---

## Phase 2: Version Alignment ✅ COMPLETE

Align dependency versions across the two apps to reduce duplication in shared packages.

| Task | Status | Notes |
|------|--------|-------|
| React version alignment | Done | Both use React 18 (frontend 18.3, admin 18.2) |
| Vite plugin alignment | Done | Both use `@vitejs/plugin-react-swc` (Vite 5) |
| Shared UI component extraction | Done | ~20 components extracted: Button, Card, Dialog, DropdownMenu, Form, Input, Label, Select, Table, Tooltip + shadcn wrappers |
| Pnpm v10 compatibility | Done | `onlyBuiltDependencies=esbuild` approved (3 versions needed) |

---

## Phase 3: Shared Package Extraction ✅ IN PROGRESS

Extract reusable code into workspace packages.

| Task | Status | Notes |
|------|--------|-------|
| `@stipendariet/ui` (shared components) | Done | ~20 shared components, barrel exports in `src/index.tsx` |
| `@stipendariet/types` (shared types) | Done | User, Profile, LifeSituation, HealthCondition, Occupation, SupportPurpose, Grant, Application, GrantsResponse, MatchedFoundation, County, Municipality |
| `@stipendariet/eslint-config` | Done | Flat config matching main frontend's v9 setup |
| `@stipendariet/api-client` | Not started | Backend API client shared between apps and admin |
| Shared hooks/libraries | Not started | Identify overlap in utility functions, custom hooks across both frontends |
| Frontend wired to shared types | Done | `types/grants.ts` re-exports from `@stipendariet/types`; `api.ts`, `AuthContext` use shared types |
| Admin wired to shared types | Done | `types/index.ts` re-exports `User` from `@stipendariet/types` |

---

## Phase 4: Backend Integration ✅ IN PROGRESS

Integrate the Python backend into Turbo pipeline and create an API client.

| Task | Status | Notes |
|------|--------|-------|
| Docker compose local dev | Done | `docker compose up -d` starts all services from monorepo root |
| Backend turbo bridge (`@backend/build`) | Done | Calls `docker compose build backend` |
| Backend lint in CI (ruff) | Done | Runs `ruff check` before Docker build in CI pipeline |
| `@stipendariet/api-client` | Not started | TypeScript fetch wrapper for FastAPI endpoints |
| Shared types aligned with backend models | Partially done | User, Profile extracted; need review against backend Pydantic models |
| Backend tests in CI (pytest) | Not started | Should run tests before Docker build |

---

## Phase 5: CI/CD ✅ IN PROGRESS

Automated pipeline covering lint → test → build → Docker push.

### Current State

**CI workflow** (`.github/workflows/ci.yml`) is live on every push to main + PRs:

| Task | Status | Notes |
|------|--------|-------|
| Lint job | Done | Runs `pnpm turbo run lint` across all workspace packages |
| Test job | Done | Builds shared packages first, then runs `vitest` — all 151 tests pass |
| Build job | Done | Turbo builds types → ui → frontend/admin in dependency order |
| Docker build+push | Done | `needs: [lint, test, build]` — only pushes images on main branch |

### Still Needed
| Task | Status | Notes |
|------|--------|-------|
| Admin vitest setup | Not started | Admin has no test suite; should set up vitest with jsdom |
| Backend pytest in CI | Not started | Run backend tests before Docker build |
| Backend ruff config | Not started | Add pyproject.toml with consistent ruff rules |
| Docker multi-platform pushes | Waiting for green CI run | amd64 + arm64 for all 3 services |
| @stipendariet/api-client | Not started | Shared API client for frontend + admin |
| Shared hooks/libraries | Not started | Extract duplicate logic across apps |

### Resolved (fixed)
1. ✅ **@stipendariet/ui resolution in tests** — fixed by importing via `import type` (types-only package)
2. ✅ **Missing swedish-regions.ts file** — stopped being gitignored by anchoring `.gitignore` rule to `/data/`
3. ✅ **Docker build ordering** — `needs: [lint, test, build]` instead of just `needs: lint`
4. ✅ **Duplicate User/Profile types** — unified across frontend and admin via `@stipendariet/types`
5. ✅ **Frontend tests pass** — all 151 pass, 4 skipped (pre-existing skips)
6. ✅ **Backend lint in CI** — `ruff check` runs before Docker build
7. ✅ **eslint-config missing build script** — added no-op build script

### Open
- None currently blocking CI

---

## Known Issues & Technical Debt

All originally identified issues are now resolved. Remaining items are feature work, not debt:

### Backlog
1. **Admin test setup** — needs vitest + jsdom config (no existing tests)
2. **Backend pytest in CI** — add `pytest` run before Docker build
3. **Backend ruff config** — add `pyproject.toml` with consistent rule set
4. **@stipendariet/api-client** — shared TypeScript fetch wrapper for FastAPI endpoints
5. **Backend types alignment** — review shared `User`/`Profile` against backend Pydantic models
6. **Shared hooks/libraries** — extract duplicate custom hooks and utility functions

---

## Decision Log

| Date | Decision | Reasoning |
|------|----------|-----------|
| 2025-06 | Backend excluded from pnpm workspace | Python has no npm dependencies; only integrated via docker compose turbo bridge |
| 2025-06 | `@stipendariet/*` scope for workspace packages | Consistent naming, avoids name collisions with other projects |
| 2025-06 | pnpm v10 with `onlyBuiltDependencies=esbuild` | pnpm v10 requires explicit build script approval; esbuild is only built dependency needed across both apps |
