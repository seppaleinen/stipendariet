# Testing

This document covers how tests are structured and run across the StipendieAssistenten monorepo.

## Test Architecture

The project follows the standard testing pyramid: many fast **unit tests**, a layer of **integration tests**, and a smaller set of **end-to-end tests** that exercise the full stack.

```
        /\
       /  \           E2E (Playwright) — frontend user flows
      /----\
     /      \         Integration — frontend↔backend (vitest + running backend)
    /--------\
   /          \       Unit — pure logic, components, hooks (vitest / pytest)
  /____________\
```

| Tier | Framework | Where | Speed | Scope |
|------|-----------|-------|-------|-------|
| Unit (frontend) | Vitest + Testing Library | `apps/{frontend,admin}/src/**` | Fast (ms) | Components, hooks, pure utilities, contexts |
| Unit (backend) | pytest | `backend/test_*.py`, `backend/tests/` | Fast (ms) | Services, routers, models, validation |
| Integration | Vitest + running backend | `apps/frontend/src/lib/api.integration.test.ts` | Medium (s) | `@stipendariet/api-client` against live FastAPI |
| E2E | Playwright | `apps/frontend/e2e/` | Slow (s) | Browser flows across Chromium / Firefox / WebKit |

### Frontend unit tests

- **Framework:** Vitest 3 with jsdom + `@testing-library/react`.
- **Setup file:** `src/test-setup.ts` — mocks `react-router-dom`, `react-helmet-async`, `IntersectionObserver`, `ResizeObserver`, `scrollIntoView`, `matchMedia`, `fetch`, `localStorage`, `TextEncoder`/`TextDecoder`.
- **Coverage gates** (enforced by Vitest thresholds in `apps/frontend/vitest.config.ts` for `src/lib/utils.ts` and `src/lib/page-metadata.ts`):
  - Lines: **80%**
  - Branches: **75%**
  - Functions: **85%**
- **Aliases:** `@/` → `src/` (per-app, via Vite resolve).

### Backend tests

- **Framework:** pytest + pytest-asyncio. No shared `conftest.py`; tests are run individually per file (see the `backend/AGENTS.md` gotcha).
- **Config:** `[tool.pytest.ini_options]` lives in `backend/pyproject.toml` (`pythonpath = ["."]`).
- **Async:** tests use `@pytest.mark.asyncio` where applicable.
- **Database:** integration tests rely on the real Postgres + pgvector container (see `docker-build` job in CI).

## Running Tests

### All tiers (Turbo, runs each workspace's `test` task)

```bash
pnpm run test
```

This invokes `turbo run test` across `apps/*` and `packages/*`. Each app runs `vitest run` once.

### Frontend only

```bash
# Unit tests
pnpm --filter @stipendariet/frontend test

# Coverage report (HTML + text + json)
pnpm --filter @stipendariet/frontend test:coverage

# Interactive UI
pnpm --filter @stipendariet/frontend test:ui

# Integration (requires backend running — see note below)
pnpm --filter @stipendariet/frontend test:api-integration
```

The integration suite (`apps/frontend/src/lib/api.integration.test.ts`) hits the real FastAPI service. Start the backend first:

```bash
pnpm run dev:infra    # Postgres + Redis + Browserless via Docker
cd backend && uvicorn app.main:app --reload --port 8000
```

### Admin only

```bash
pnpm --filter @stipendariet/admin test
pnpm --filter @stipendariet/admin test:coverage
```

Admin does not currently ship an E2E or integration suite — coverage is via Vitest unit tests only.

### Backend only

```bash
cd backend
pip install -r requirements.txt pytest pytest-asyncio httpx
pytest -v
# or a single file
pytest tests/test_pipeline.py
```

> Per `backend/AGENTS.md`, tests are run **individually per file** (no shared `conftest.py`); the `pytest -v` invocation in CI walks all of them.

### End-to-end (Playwright)

```bash
# Frontend only — starts its own dev server on port 8080
pnpm --filter @stipendariet/frontend test:e2e

# UI mode
pnpm --filter @stipendariet/frontend test:e2e:ui

# Debug mode
pnpm --filter @stipendariet/frontend test:e2e:debug
```

Playwright config (`apps/frontend/playwright.config.ts`) runs against Chromium, Firefox, and WebKit and uses an `auth.setup.ts` project to seed storage state for the others.

### Everything

```bash
pnpm run test:all      # runs `turbo run test test:e2e`
```

## Coverage Status

Counts below reflect the test inventory landed through the audit (#1) Phases A–D. Numbers are approximate — regenerate locally before quoting.

| Surface | Framework | Tests | Coverage gates | Notes |
|---------|-----------|------:|----------------|-------|
| `apps/frontend` | Vitest + RTL + Playwright | ~185+ | 80/75/85 (utils, page-metadata only) | Hooks + components audited in Phase A |
| `apps/admin` | Vitest + RTL | ~53 | None enforced | Module coverage landed in Phase D |
| `backend/` | pytest + pytest-asyncio | ~267 | None enforced | Failure-mode coverage landed in Phase C |
| E2E (Playwright) | Playwright | flows in `e2e/flows/` | — | Smoke + onboarding + applications |

### What's covered well

- **Frontend components and contexts:** `AuthContext`, `ProfileContext`, `SEOHead`, `ProtectedRoute`, `ProfileSwitcher`, `Layout`, `GrantDetail`, `utils`, `page-metadata`, `prompt-builder`, `api`.
- **Admin module:** dedicated Phase D suite covering core admin functionality.
- **Backend failure modes:** Phase C added explicit negative-path tests for routers/services.

### Known gaps

- Admin has no enforced coverage thresholds in `apps/admin/vitest.config.ts` (intentionally minimal config — admin runs through the same `vitest run` flow but without gates).
- Frontend coverage gates are scoped narrowly (only `lib/utils.ts` and `lib/page-metadata.ts`); wider surface coverage is incremental.
- Backend has no `--cov` run wired into the test command — pytest is invoked with `-v` only in CI.

## CI/CD Integration

Workflow: `.github/workflows/ci.yml`. It runs on every push to `main` and every PR against `main`, with `concurrency.cancel-in-progress: true`.

The pipeline runs **four sequential jobs with explicit gates** — `docker-build` only proceeds if all upstream jobs pass:

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────────────────┐
│  lint   │ ─► │  test   │ ─► │  build  │ ─► │   docker-build   │
└─────────┘    └─────────┘    └─────────┘    └──────────────────┘
      │              │              │                │
      ▼              ▼              ▼                ▼
   pnpm lint     vitest run    turbo build     pytest + docker
                 (frontend +    (all)          buildx multi-arch
                  admin)                         + Helm push
```

### Job breakdown

1. **`lint`** — `pnpm install --frozen-lockfile` then `pnpm lint` across the workspace.
2. **`test`** — builds shared packages (`@stipendariet/types`, `api-client`, `ui`, `eslint-config`) first (`dependsOn: ["^build"]` in `turbo.json`), then runs `npx vitest run` in `apps/frontend` and `apps/admin`. Backend unit tests are **not** in this job — they live in `docker-build`.
3. **`build`** — `pnpm turbo run build`. Prerender (`scripts/prerender.js`) and sitemap generation are part of `apps/frontend`'s build script and run only when this job succeeds.
4. **`docker-build`** — gates on `lint + test + build`. Spins up a Postgres + pgvector service container, then:
   - Lints backend with `ruff check .`
   - Runs `pytest -v` against the live DB
   - Sets up QEMU + Buildx for multi-arch (linux/amd64, linux/arm64) builds
   - On `push` to `main`: builds and pushes `backend`, `frontend`, and `admin` images to GHCR; packages and pushes Helm charts (`backend`, `frontend`, `admin-frontend`) to `oci://ghcr.io/${{ repo }}/charts`.

### Why backend tests live in `docker-build`

Backend tests need a real Postgres + pgvector. Rather than spin up Postgres inside the Node-only `test` job, the workflow reuses the Postgres service container that `docker-build` already requires for image work. This keeps the `test` job fast and Node-only while still gating releases on backend correctness.

### Caching

- pnpm store cached via `actions/cache@v4` keyed by `pnpm-lock.yaml` hash.
- Docker layers cached via `docker/build-push-action@v5` with `cache-from`/`cache-to: type=gha` scoped per image (`ci-backend`, `ci-frontend`, `ci-admin`).

### Local hooks

`.githooks/pre-push` runs `ruff check .` over `backend/` and blocks the push on lint errors. Activate with:

```bash
git config core.hooksPath .githooks
```

## Test Audit Phases (Issue #1)

Reference: the test audit tracked in issue #1. The status below reflects what is currently committed on `main`.

| Phase | Focus | Status | Outcome |
|-------|-------|:------:|---------|
| A | Frontend hooks + components | ✅ Done | `test(audit#1)` — `AuthContext`, `ProfileContext`, `SEOHead`, `ProtectedRoute`, `ProfileSwitcher`, `Layout`, `GrantDetail` |
| B | _(future)_ | — | Held for later audit work |
| C | Backend failure modes | ✅ Done | `test(audit#1): add Phase C failure mode tests for backend` (commit `fa3e288`) |
| D | Admin module coverage | ✅ Done | `test(admin): add phase-d admin module tests` (commit `be18bba`) |
| F | This document | ✅ Done | `TESTING.md` |

Phase F is the documentation closeout — it lands after the code/test phases because the numbers and coverage shape can only be reported once they exist.

## Conventions

- **File placement:** tests live next to the code they exercise (`foo.ts` ↔ `foo.test.ts`), except Playwright which lives under `apps/frontend/e2e/`.
- **Naming:** `*.test.{ts,tsx}` for Vitest, `test_*.py` for pytest.
- **Async backend tests:** mark with `@pytest.mark.asyncio`.
- **Frontend mocks:** global mocks belong in `src/test-setup.ts`; per-test mocks use `vi.mock(...)` inline.
- **Don't commit secrets or live API tokens** into test fixtures — backend tests rely on the GH Actions service container, not real credentials.