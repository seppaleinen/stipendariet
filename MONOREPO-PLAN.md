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

## Phase 2: Version Alignment ✅ IN PROGRESS

Align dependency versions across the two apps to reduce duplication in shared packages.

| Task | Status | Notes |
|------|--------|-------|
| React version alignment | Done | Both use React 18 (frontend 18.3, admin 18.2) |
| Vite plugin alignment | In Progress | Frontend uses `@vitejs/plugin-react-swc` (Vite 5); admin switching to same for consistency |
| Shared UI component extraction | Done | ~20 components extracted: Button, Card, Dialog, DropdownMenu, Form, Input, Label, Select, Table, Tooltip + shadcn wrappers |
| Pnpm v10 compatibility | Done | `onlyBuiltDependencies=esbuild` approved (3 versions needed) |

**Pending**: Complete admin Vite plugin migration to SWC variant.

---

## Phase 3: Shared Package Extraction ⏳ NOT STARTED

Extract reusable code into workspace packages.

| Task | Status | Notes |
|------|--------|-------|
| `@stipendariet/ui` (shared components) | Done | ~20 shared components, barrel exports in `src/index.tsx` |
| `@stipendariet/types` (shared types) | In Progress | Foundation/Scholarship types extracted from frontend; more to come |
| `@stipendariet/eslint-config` | Done | Flat config matching main frontend's v9 setup |
| `@stipendariet/api-client` | Not started | Backend API client shared between apps and admin |
| Shared hooks/libraries | Not started | Identify overlap in utility functions, custom hooks across both frontends |

---

## Phase 4: Backend Integration ⏳ NOT STARTED

Integrate the Python backend into Turbo pipeline and create an API client.

| Task | Status | Notes |
|------|--------|-------|
| Docker compose local dev | Done | `docker compose up -d` starts all services from monorepo root |
| Backend turbo bridge (`@backend/build`) | Done | Calls `docker compose build backend` |
| API client package (`@stipendariet/api-client`) | Not started | TypeScript fetch wrapper for FastAPI endpoints |
| Shared types (Foundation, Scholarship) | In Progress | Partial extraction from frontend; needs review against backend model |

---

## Phase 5: CI/CD ⏳ IN PROGRESS

Automated pipeline covering lint → test → build → Docker push.

### Current State

**CI workflow** (`.github/workflows/ci.yml`) is live and running on every push to main + PRs, but has issues:

| Task | Status | Notes |
|------|--------|-------|
| Lint job | Done | Runs `pnpm turbo run lint` across all apps |
| Test job | **Broken** — @stipendariet/ui resolution fails (`dist/index.js` missing) | Need to build shared packages before vitest runs |
| Build job | Done (passes now) | Builds types + ui; frontend/admin pass; eslint-config has no `build` script |
| Docker build+push | **Broken** — depends only on lint, not test/build | Should depend on all previous jobs passing first |
| Missing file in CI | **Broken** — `src/data/swedish-regions.ts` tracked locally but gitignored | `.gitignore` rule `data/` catching nested paths; need `/data/` anchor |

### Pending Fixes (2d60bea pushed, awaiting results)
- Build shared packages (`types`, `ui`, `eslint-config`) before vitest in test job
- Change Docker build `needs: [lint, test, build]` instead of just `needs: lint`
- Anchor `.gitignore` rule from `data/` → `/data/` to allow nested `src/data/`

### Still Needed
| Task | Status | Notes |
|------|--------|-------|
| Admin tests | Not started | Admin has no test suite yet; may need vitest setup |
| Backend lint (ruff) | Not started | Python linting step before Docker build |
| Docker multi-platform pushes | Blocked by CI failures above | amd64 + arm64 for both backend and admin services |

---

## Known Issues & Technical Debt

### Critical (Blocking CI)
1. **@stipendariet/ui resolution in tests** — vitest can't resolve the package because dist/ doesn't exist yet; shared packages must be built first
2. **Missing swedish-regions.ts file** — imported by ProfileSetup.tsx, exists locally but gitignored
3. **Docker build ordering** — should depend on all previous jobs passing

### Medium (Non-blocking)
4. **Admin Vite plugin migration** — needs `@vitejs/plugin-react-swc` for SWC consistency with frontend
5. **esbuild versions in CI** — admin's Vite 4 uses esbuild ~0.18, frontend's Vite 5 uses esbuild ~0.25; need to ensure all versions are available during build

### Low (Cosmetic)
6. **eslint-config has no `build` script** — but it has a `build` in turbo.json; should add one or remove from pipeline
7. **Backend types not aligned with frontend types** — Foundation/Scholarship types extracted partially, need review against backend models

---

## Decision Log

| Date | Decision | Reasoning |
|------|----------|-----------|
| 2025-06 | Backend excluded from pnpm workspace | Python has no npm dependencies; only integrated via docker compose turbo bridge |
| 2025-06 | `@stipendariet/*` scope for workspace packages | Consistent naming, avoids name collisions with other projects |
| 2025-06 | pnpm v10 with `onlyBuiltDependencies=esbuild` | pnpm v10 requires explicit build script approval; esbuild is only built dependency needed across both apps |
