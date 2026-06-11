# Monorepo Migration Audit

> Generated: 2026-06-11 | Updated: 2026-06-11 (implementation pass)
> Auditing: `stipendie-assistenten` (GitHub org) → `stipendariet` (monorepo) + `fleet-infra` (Flux)

## Status Update — Implementation Completed

| Task | Status | Details |
|------|--------|---------|
| ~~Migrate Playwright E2E tests~~ | ✅ | **Done** — `apps/frontend/e2e/frontend-smoke.spec.ts` + `playwright.config.ts` + dep in `package.json` |
| ~~Admin test suite~~ | ✅ | **Done** — `vitest.config.ts`, `test-setup.ts`, `App.test.tsx`, wired to CI |
| ~~Backend pytest in CI~~ | ✅ | **Done** — Added `pip install pytest ... && pytest -v` to `ci.yml` docker-build job |
| ~~Helm charts from fleet-infra~~ | ✅ | **Done** — Replaced stale `kubernetes/{backend,frontend,admin-frontend}/` with production charts at `kubernetes/charts/stipendiatet/{backend,frontend,admin-frontend}/`. Includes browserless, enrichment-worker, ingress templates from fleet-infra |
| ~~Release workflow~~ | ✅ | **Done** — `.github/release.yml` — on `v*` tag push: builds Docker images + Helm charts, pushes to GHCR with semver tags |
| ~~Helm publish on main~~ | ✅ | **Done** — Added to `ci.yml` — packages/pushes charts as `0.0.0+git.<sha>` to `oci://ghcr.io/.../charts/` |
| Wire `@stipendariet/api-client` into apps | ✅ | **Done** — Admin uses it instead of `axios` (removed dep). Frontend uses it internally instead of raw `fetch`. Both via `createApiClient` with automatic auth |
| Monorepo-aware Dockerfiles | ✅ | **Done** — Both frontend & admin Dockerfiles now use pnpm workspace build (context: repo root) |
| ~~Archive old GitHub repos~~ | ✅ | **Done** — Archived 6 repos in `stipendie-assistenten` org: `backend`, `stipendium-assistenten-frontend`, `stipendie-admin`, `infra-docs`, `data-engine`, `infra-test` |

---

## 1. Repo-by-Repo Migration Status

### 1.1 `stipendie-assistenten/backend` — ✅ FULLY MIGRATED — CAN ARCHIVE

| Item | Status |
|------|--------|
| FastAPI app source | ✅ `monorepo/backend/app/` — all routers, models, services |
| Alembic migrations | ✅ `monorepo/backend/alembic/` — all 8 versions present |
| Tests | ✅ `monorepo/backend/tests/` — all 8 test files |
| Dockerfile | ✅ `monorepo/backend/Dockerfile` |
| pyproject.toml (ruff config) | ✅ `monorepo/backend/pyproject.toml` |
| Requirements | ✅ `monorepo/backend/requirements.txt` |
| AGENTS.md | ✅ `monorepo/backend/AGENTS.md` |
| Backend spec | ✅ `monorepo/backend/backend-spec.yaml` |

**Verdict:** Old repo is fully superseded. Archive on GitHub.

### 1.2 `stipendie-assistenten/stipendium-assistenten-frontend` — ✅ FULLY MIGRATED — CAN ARCHIVE

| Item | Status |
|------|--------|
| App source | ✅ `monorepo/apps/frontend/src/` — all pages, components, hooks |
| UI components | ✅ Extracted to `monorepo/packages/ui/` (shared with admin) |
| Tests | ✅ `monorepo/apps/frontend/vitest.config.ts` — 151 tests |
| Dockerfile | ✅ `monorepo/apps/frontend/Dockerfile` |
| SEO/robots/sitemap | ✅ `monorepo/apps/frontend/public/` |
| CI integration | ✅ `.github/workflows/ci.yml` — lint, test, build, push |

**Verdict:** Old repo is fully superseded. Archive on GitHub.

### 1.3 `stipendie-assistenten/stipendie-admin` — ✅ FULLY MIGRATED — CAN ARCHIVE

| Item | Status |
|------|--------|
| App source | ✅ `monorepo/apps/admin/src/` — all pages, hooks, components |
| Shared UI | ✅ Using `@stipendariet/ui` from packages |
| Dockerfile | ✅ `monorepo/apps/admin/Dockerfile` |
| CI integration | ✅ `.github/workflows/ci.yml` — build + push |

**Verdict:** Old repo is fully superseded. Archive on GitHub.
**Note:** Admin still has zero tests — tracked below in gaps.

### 1.4 `stipendie-assistenten/infra-docs` — ✅ PARTIALLY MIGRATED — MOSTLY SUPERSEDED

| Item | Status |
|------|--------|
| Helm charts (stipendiatet/) | ✅ Migrated to both `monorepo/kubernetes/` AND `fleet-infra/flux/stipendiatet/` — fleet-infra has the **active production** charts (includes browserless, enrichment worker) |
| Deployment scripts | ✅ `monorepo/scripts/dev_deploy.bash`, `prod_deploy.bash` |
| SYSTEM_OVERVIEW.md | ✅ `monorepo/docs/SYSTEM_OVERVIEW.md` |
| admin-interface-spec.md | ✅ `monorepo/docs/admin-interface-spec.md` |
| data-engine-spec.md | ✅ `monorepo/docs/data-engine-spec.md` |
| docker-compose.yml | ✅ `monorepo/docker-compose.yml` (evolved version) |
| DB init scripts | ✅ `monorepo/db/init/` |
| **BDD tests (bdd-tests/)** | ❌ **Not migrated** — Python behave tests for enrichment pipeline |
| **Planning docs (.conductor/)** | ❌ Not migrated — historical planning artifacts |
| **Planning docs (tracks/)** | ❌ Not migrated — historical planning artifacts |

**Verdict:** The infra-docs repo contains:
- Helm charts → active in fleet-infra, not needed in old repo
- BDD tests → should be migrated to monorepo if still relevant
- Planning artifacts → archive-only value

### 1.5 `stipendie-assistenten/data-engine` — 🟡 SUPERSEDED / OBSOLETE

**Analysis:** This was an earlier version of the backend focused on scholarship data with pgvector embeddings. Its structure (`app/models/scholarship.py`, `app/api/scholarships.py`, standalone `app/services/llm/`) has been refactored into the monorepo backend's `app/foundation/`, `app/pipeline/`, `app/db/`, and `app/services/` directories.

| Item | Status |
|------|--------|
| Scholarship CRUD | ✅ Superseded by `monorepo/backend/app/api/v1/routers/` |
| LLM service | ✅ Superseded by `monorepo/backend/app/services/` |
| Scraper service | ✅ Superseded by `monorepo/backend/app/services/scraper_service.py` |
| pgvector embedding | ✅ Superseded by `monorepo/backend/app/db/` + embedding_service |

**Verdict:** No unique functionality. Archive on GitHub.
**Safety check:** Verify the old embedding column logic (`ensure_embedding_column`) is not needed — the monorepo backend uses alembic for schema management.

### 1.6 `stipendie-assistenten/infra-test` — ❌ NOT MIGRATED

| Item | Status |
|------|--------|
| Playwright E2E tests | ❌ `playwright/tests/frontend-combined-test.spec.ts` — not in monorepo |
| Playwright config | ❌ Not in monorepo |

**Verdict:** E2E tests should be migrated to `monorepo/apps/frontend/e2e/` or `monorepo/e2e/` with Playwright config.

---

## 2. Fleet-Infra Cross-Reference

### Active Flux configuration (`fleet-infra/flux/stipendiatet/`)

| Component | Source | Image |
|-----------|--------|-------|
| backend | Fleet-infra Helm chart | `seppaleinen/stipendariet-backend` (Docker Hub) |
| frontend | Fleet-infra Helm chart | `seppaleinen/stipendariet-frontend` (Docker Hub) |
| admin-frontend | Fleet-infra Helm chart | `seppaleinen/stipendariet-admin` (Docker Hub) |

### Image registry mismatch ⚠️

| Environment | Backend image | Frontend image | Admin image |
|-------------|---------------|----------------|-------------|
| CI build pushes to | `ghcr.io/*/backend` | `ghcr.io/*/frontend` | `ghcr.io/*/admin` |
| Flux expects from | `seppaleinen/stipendariet-backend` | `seppaleinen/stipendariet-frontend` | `seppaleinen/stipendariet-admin` |

**The CI workflow and Flux config push/pull from different registries.** The CI pushes to GHCR but Flux pulls from Docker Hub (`seppaleinen`). This means CI builds are effectively not reaching production — Flux still pulls older Docker Hub images.

### Chart divergence ⚠️

Monorepo `kubernetes/` charts are simplified copies of the production charts in `fleet-infra`. Fleet-infra has additional templates not in the monorepo:
- `browserless-deployment.yaml`, `browserless-service.yaml`
- `enrichment-worker-deployment.yaml`
- topology spread constraints

**The monorepo kubernetes/ directory is stale.** The source of truth for k8s manifests is `fleet-infra/flux/stipendiatet/`.

### Old repo references in fleet-infra
- **No references** to any `stipendie-assistenten` repos found in fleet-infra
- All Flux sources point to the fleet-infra repo itself (self-referencing GitRepository for Helm charts)

---

## 3. Monorepo Internal Gaps

### 3.1 `@stipendariet/api-client` — EXISTS BUT NOT WIRED 🔌

**Status:** Package scaffolded with a solid `createApiClient()` factory (zero-dependency fetch client).
**Gap:** Neither `apps/frontend` nor `apps/admin` imports it:
- `apps/frontend/src/lib/api.ts` — standalone fetch wrapper (duplicate logic)
- `apps/admin` uses `axios` directly (different dependency, heavier)
- Both should migrate to `@stipendariet/api-client` to centralize auth token logic, error handling, and base URL config

**Action:** Wire api-client into both apps, remove axios from admin, replace frontend's api.ts with api-client.

### 3.2 Admin has zero tests 🧪

**Status:** `apps/admin/package.json` has no `test` script, no `vitest`, no `jsdom`.
**Gap:** CI `test` job only runs frontend tests. Admin is completely untested.
**Action:** Add vitest + jsdom, write initial smoke tests, add to CI pipeline.

### 3.3 Backend pytest not in CI 🐍

**Status:** Backend has 8 test files (pytest + pytest-asyncio) but CI only runs `ruff check`.
**Gap:** No `pytest` step before Docker build.
**Action:** Add `pip install -r requirements.txt && pip install pytest pytest-asyncio && pytest` to the docker-build CI step.

### 3.4 Monorepo Dockerfiles are standalone (not monorepo-aware) 🐳

**Status:** CI comment says "Frontend and admin Dockerfiles are currently standalone (per-app npm deps). For production monorepo Docker builds, these will need monorepo-aware Dockerfiles."
**Gap:** The Dockerfiles do `COPY package.json` from the app directory only, not from the workspace root. This means they can't leverage pnpm workspace caching or shared packages at build time. The `@stipendariet/ui` is resolved via workspace protocol and needs the monorepo context.
**Action:** Refactor Dockerfiles to be monorepo-aware (install pnpm, copy workspace root, build from root context).

### 3.5 Image registry mismatch (CI → Flux) 🔄

**Gap:** CI pushes to GHCR but Flux pulls from Docker Hub. These need to be aligned.
**Action:** Either:
- (a) Change CI to push to Docker Hub `seppaleinen/*` (simpler, matches current Flux config), OR
- (b) Change Flux to pull from GHCR (requires updating secrets in cluster), OR
- (c) Both (push to both registries during transition)

### 3.6 Monorepo kubernetes/ charts are stale 📦

**Status:** The `monorepo/kubernetes/` directory has simpler Helm charts that lack browserless, enrichment worker, topology spread, etc.
**Gap:** Source of truth for k8s manifests is `fleet-infra/flux/stipendiatet/`.
**Action:** Either:
- (a) Remove `monorepo/kubernetes/` and point users to fleet-infra, OR
- (b) Sync monorepo charts with fleet-infra (make fleet-infra the automation source)

### 3.7 Shared hooks/libraries not extracted 🪝

**Status:** `MONOREPO-PLAN.md` lists this as "Not started". Common patterns between frontend and admin (auth context patterns, utility functions) have not been extracted to shared packages.

### 3.8 Backend types alignment with Pydantic models 🔍

**Status:** `MONOREPO-PLAN.md` lists this as "Partially done". `@stipendariet/types` has User/Profile types but these need review against the backend Pydantic models in `app/db/schemas.py` and `app/db/models.py`.

---

## 4. Migration Action Plan

### Phase A: Archive old repos (immediate, low risk) ⬆️
1. Archive `stipendie-assistenten/backend` (fully migrated)
2. Archive `stipendie-assistenten/stipendium-assistenten-frontend` (fully migrated)
3. Archive `stipendie-assistenten/stipendie-admin` (fully migrated)
4. Archive `stipendie-assistenten/data-engine` (superseded)
5. Archive `stipendie-assistenten/infra-docs` (content migrated or in fleet-infra)
6. Keep `stipendie-assistenten/infra-test` for now until Playwright tests are migrated

### Phase B: CI/Flux alignment (high priority) 🔴
1. Align image registry: decided GHCR-only ✅
2. ✅ Backend pytest in CI — Done
3. ✅ Monorepo-aware Dockerfiles — Done

### Phase C: Monorepo hardening (medium priority) 🟡
1. ✅ Wire `@stipendariet/api-client` into frontend and admin — Done
2. ✅ Remove `axios` from admin — Done (replaced by `@stipendariet/api-client`)
3. ✅ Admin test suite — Done
4. ✅ Monorepo-aware Dockerfiles — Done

### Phase D: Migration completion (lower priority) 🟢
1. ✅ Playwright E2E tests — Done
2. ✅ Helm charts from fleet-infra — Done (at `kubernetes/charts/stipendiatet/`)
3. ✅ Release workflow — Done
4. ✅ Archive old GitHub repos — Done (archived 6 repos in `stipendie-assistenten` org)
5. Extract shared hooks/libraries into `@stipendariet/hooks`
6. Align `@stipendariet/types` with backend Pydantic models
7. Migrate BDD tests from infra-docs if still relevant

### Phase E: Cleanup (ongoing) 🔵
1. Remove reference to `stipendie-assistenten` from backend/LICENSE (cosmetic)
2. Update MONOREPO-PLAN.md with current status

---

---

## 5. Helm Chart Move & Release Pipeline Plan

### Goal
Move the active production Helm charts from `fleet-infra/flux/stipendiatet/` into the monorepo as the single source of truth. CI builds both Docker images and Helm charts, pushing them to GHCR with release versioning.

---

### 5.1 Proposed Structure

```
monorepo/
  kubernetes/
    charts/                              # ← NEW: production Helm charts, copied from fleet-infra
      stipendiatet/
        backend/
          Chart.yaml                     # apiVersion: v2, name: stipendiatet-backend
          values.yaml                    # Generic defaults (image repo/tag, envs, resource requests)
          templates/
            backend-deployment.yaml      # From fleet-infra (with probes, topology spread)
            backend-service.yaml         # From fleet-infra
            browserless-deployment.yaml  # From fleet-infra
            browserless-service.yaml     # From fleet-infra
            enrichment-worker-deployment.yaml  # From fleet-infra
            environment-secrets.yaml     # From fleet-infra (templated secret)
        frontend/
          Chart.yaml                     # name: webapp (match fleet-infra naming)
          values.yaml                    # Host, image, resources
          templates/
            deployment.yaml              # From fleet-infra
            environment-secrets.yaml     # From fleet-infra
            ingress.yaml                 # From fleet-infra (Traefik annotations)
            service.yaml                 # From fleet-infra
        admin-frontend/
          Chart.yaml                     # name: admin-frontend
          values.yaml                    # Host, image, resources, backend URL
          templates/
            deployment.yaml              # From fleet-infra
            environment-secrets.yaml     # From fleet-infra
            ingress.yaml                 # From fleet-infra (Traefik annotations)
            service.yaml                 # From fleet-infra
    postgres/                            # Keep as-is (local dev postgres secrets)
    helmfile.yaml                        # Updated to reference ../charts/ paths
    sops.yaml                            # Keep as-is
```

**Key differences from current `monorepo/kubernetes/`:**
- Adds `browserless-*` and `enrichment-worker-*` templates (currently only in fleet-infra)
- Adds topology spread constraints to backend deployment
- `environment-secrets.yaml` uses `range` over `.Values.secrets` (from fleet-infra) instead of hardcoded env vars
- Adds ingress templates (currently missing from monorepo backend chart)

**What stays in fleet-infra:**
- `HelmRelease` CRDs (`helmrelease.yaml`, `kustomization.yaml`) — Flux-specific
- `secrets.yaml` — SOPS-encrypted production secrets
- `flux-system` `GitRepository` reference — no change needed since Flux reads the rest from fleet-infra

---

### 5.2 Versioning Strategy

| Trigger | Docker tags | Helm chart tags |
|---------|-------------|-----------------|
| Tag push `v1.2.3` | `v1.2.3` + `latest` | `1.2.3` + `latest` |
| Push to `main` | `latest` only | `latest` only |
| PR | no push (build-only) | no push |

**Single-version-per-release.** All three components (backend, frontend, admin-frontend) are tagged with the same version tag from `git describe`. No independent versioning per component.

**Helm chart appVersion:** Set to the git tag (e.g. `1.2.3`). Chart `version` also matches.

**Image naming:**
```
ghcr.io/seppaleinen/stipendariet/backend:v1.2.3
ghcr.io/seppaleinen/stipendariet/frontend:v1.2.3
ghcr.io/seppaleinen/stipendariet/admin:v1.2.3
```

**Helm chart OCI paths:**
```
oci://ghcr.io/seppaleinen/stipendariet/charts/backend:v1.2.3
oci://ghcr.io/seppaleinen/stipendariet/charts/frontend:v1.2.3
oci://ghcr.io/seppaleinen/stipendariet/charts/admin-frontend:v1.2.3
```

---

### 5.3 CI/CD Workflow Design

**Recommended: New `release.yml` workflow** (separate from the existing `ci.yml` which stays for PR validation).

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  docker:
    name: Build & Push Docker Images
    runs-on: ubuntu-latest
    steps:
      - checkout
      - setup-node + pnpm
      - Docker buildx + QEMU
      - Build all 3 images (backend, frontend, admin-frontend)
      - Push to GHCR with tag derived from git ref

  helm:
    name: Package & Push Helm Charts
    needs: docker           # ensure images exist before chart release
    runs-on: ubuntu-latest
    steps:
      - checkout
      - setup-helm
      - For each chart (backend, frontend, admin-frontend):
        - Update Chart.yaml version + appVersion from git tag
        - Update values.yaml image tags to matching release tag
        - `helm package`
        - `helm push` to GHCR OCI

  flux-update:              # optional, for GitOps automation
    name: Update Fleet-Infra
    needs: helm
    runs-on: ubuntu-latest
    steps:
      - Checkout fleet-infra
      - Update HelmRelease values with new image tags
      - Commit + push to fleet-infra main
```

---

### 5.4 Implementation Steps

| # | Step | Details |
|---|------|---------|
| 1 | **Copy charts** | Replace `monorepo/kubernetes/{backend,frontend,admin-frontend}/` with the production versions from `fleet-infra/flux/stipendiatet/` — place under `kubernetes/charts/stipendiatet/` |
| 2 | **Test chart linting** | Run `helm lint` on all 3 charts to catch template issues |
| 3 | **Add Helm to CI** | Install `helm` in CI runner (available by default on ubuntu-latest) |
| 4 | **Create release workflow** | `.github/workflows/release.yml` as designed above |
| 5 | **Update helmfile** | Point `kubernetes/helmfile.yaml` to `./charts/stipendiatet/backend` etc. |
| 6 | **Decide registry** | Choose GHCR (already used by CI) as single registry, or dual-push to Docker Hub + GHCR during transition |
| 7 | **Update fleet-infra** *(future)* | Change `HelmRelease` charts to pull from GHCR OCI instead of local GitRepository path |

---

### 5.5 Decisions

| Question | Decision |
|----------|----------|
| Registry | **GHCR-only.** Images and charts go to `ghcr.io/seppaleinen/stipendariet/` |
| Release cadence | **Synchronized.** Single git tag `v1.2.3` releases all three components together |
| Fleet-infra auto-update | **Deferred.** Renovate in fleet-infra will handle image tag bumps when ready — no CI step needed |
| Chart versioning | **appVersion = git tag** (bumps on code changes). **chart version** stays independent — bump only when `templates/` or `values.yaml` change |
| Rollbacks | **Fleet-infra handles it.** Revert the fleet-infra commit that changed the image tag, Flux reconciles back |

---

## 6. Summary Statistics

| Repo | Migrated | Can Archive | Unique Content Not Migrated |
|------|----------|-------------|----------------------------|
| backend | ✅ Full | ✅ Yes | None |
| stipendium-assistenten-frontend | ✅ Full | ✅ Yes | None |
| stipendie-admin | ✅ Full | ✅ Yes | None |
| infra-docs | ✅ Partial | ✅ Mostly | BDD tests, planning docs |
| data-engine | 🟡 Superseded | ✅ Yes | None (functionality merged) |
| infra-test | ❌ Not started | ⏳ Wait | Playwright E2E tests |
