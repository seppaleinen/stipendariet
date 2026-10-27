# Research Brief: Modular Refactoring Plan

**Task:** Code smell analysis and modular refactoring plan for the Stipendariet monorepo
**Domain:** Mixed (dev + devops awareness)
**Date:** 2026-10-27

---

## 1. Findings — Code Smells by Area and Principle

### HIGH PRIORITY

#### 1.1 DRY Violations — Duplicate Logic

| Location | Issue | Why It Matters |
|----------|-------|----------------|
| `backend/app/api/v1/routers/foundations.py:329-369` & `570-610` | Duplicate `parse_json_field()` helper defined twice in same file (lines 329-339 and 570-580) | Maintenance burden — bug fixes must be applied twice |
| `backend/app/db/database.py:64-220` | `create_tables()` mixes schema creation with ALTER TABLE migrations, admin user creation, and pgvector extension setup | Violates single responsibility; startup becomes slower and harder to test |
| `apps/frontend/src/lib/api.ts:218-249` & `apps/frontend/src/lib/api.ts:251-292` | `mapBackendProfileToFrontend()` and `mapFrontendProfileToBackend()` duplicate field mappings that should be symmetric | Field additions require editing two functions; easy to miss one |
| `backend/app/api/v1/routers/foundations.py` & `backend/app/api/v1/routers/foundations_api.py` | Two routers serving overlapping foundation data (`/api/foundations/stored` vs `/api/foundations-api/`) | Confusing API surface; frontend may call wrong endpoint |
| `apps/frontend/src/pages/Matching.tsx:44-70` | Direct `fetch()` call instead of using shared `api` client from `@stipendariet/api-client` | Bypasses auth token handling, error handling patterns |

#### 1.2 KISS Violations — Unnecessary Complexity

| Location | Issue | Why It Matters |
|----------|-------|----------------|
| `backend/app/api/v1/routers/foundations.py:486-524` | Complex geographic SQL filter with nested OR/AND logic for `parsed_service_area` vs official codes | Hard to modify; error-prone when requirements change |
| `backend/app/foundation/sync_service.py:1-644` | 644-line monolithic sync service mixing API polling, data transformation, categorization, translation, embedding, and task tracking | Single file does too much; impossible to unit-test in isolation |
| `backend/app/db/database.py:64-220` | 156-line `create_tables()` with 10+ ALTER TABLE checks, admin creation, and extension setup | Should be split into discrete migrations or separate concerns |
| `apps/frontend/src/contexts/AuthContext.tsx:1-214` | Auth context handles token storage, fetch calls, login/signup/logout, Google OAuth stub, AND exposes `getAuthToken()` helper | Context is doing service-layer work; hard to reuse in admin |

#### 1.3 SOLID / Separation of Concerns

| Location | Issue | Why It Matters |
|----------|-------|----------------|
| `backend/app/api/v1/routers/foundations.py:156-200` | Router imports `FoundationCategorizer` from `app.foundation.categorization.categorize_foundations` directly | Router should call a service, not import implementation details |
| `backend/app/api/admin/enrichment.py:247` | Admin endpoint imports `run_foundation_pipeline_task` from `app.pipeline.orchestrator` | Cross-module coupling; pipeline logic leaks into admin API |
| `backend/app/api/v1/routers/foundation_sync.py:96-111` | `generate-application` endpoint imports `chat_completion` from `app.services.llm_client` | Router should delegate to a service, not call LLM directly |
| `apps/frontend/src/pages/Grants.tsx:1-382` & `apps/frontend/src/pages/Matching.tsx:1-308` | Pages contain business logic (filtering, saving grants, infinite scroll) that should be in hooks or services | Pages are hard to test; logic can't be reused |
| `backend/app/crud/crud.py:1-325` | Single 325-line file handling CRUD for foundations, profiles, applications, grants, users | Should be split by entity (`crud/foundations.py`, `crud/profiles.py`, etc.) |

#### 1.4 Module Boundaries

| Location | Issue | Why It Matters |
|----------|-------|----------------|
| `packages/types/src/index.ts:1-213` | Shared types include `ExchangeResponse` (admin auth) and frontend-specific types in same file | Admin and frontend types should be separated or namespaced |
| `apps/admin/src/types/index.ts:1` | Admin defines `Scholarship` interface that doesn't exist in backend models or shared types | Type drift between admin and backend; potential runtime errors |
| `backend/app/api/v1/routers/__init__.py:1-19` | Exports `admin_password_reset` router alongside public routers | Admin routers should be in separate namespace |
| `apps/frontend/src/lib/api.ts:1-356` | Frontend API client mixes grants, profiles, applications, matching, AND admin-specific functions | Should be split by domain or use separate clients |

#### 1.5 Testability Issues

| Location | Issue | Why It Matters |
|----------|-------|----------------|
| `backend/app/db/database.py:20-47` | `create_engine_with_retry()` has hardcoded `time.sleep()` and print statements | Impossible to unit-test without mocking `time` and stdout |
| `backend/app/foundation/sync_service.py` | Functions call `sync_foundations()` which internally calls `get_db()` and `create_task()` | No dependency injection; tests must mock global state |
| `apps/frontend/src/contexts/ProfileContext.tsx:1-121` | Context directly imports and calls `apiCreateProfile` from `@/lib/api` | Hard to mock in tests; should accept API client as prop |
| `backend/app/api/admin/*.py` (8 files) | Each endpoint file imports `get_db`, models, services inline | No shared test fixtures; each test must mock imports individually |

#### 1.6 Consistency Issues

| Location | Issue | Why It Matters |
|----------|-------|----------------|
| `backend/app/api/v1/routers/` | Mix of snake_case (`foundation_sync.py`) and PascalCase imports in same directory | Inconsistent naming makes navigation harder |
| `apps/frontend/src/pages/` vs `apps/admin/src/pages/` | Frontend uses co-located tests (`*.test.tsx`), admin has separate test structure | Confusing for developers moving between apps |
| `backend/app/services/` | `enrichment_schemas.py` defines class-based enums, while other files use string constants | Inconsistent pattern for constants/enums |
| `apps/frontend/src/lib/api.ts` & `apps/admin/src/lib/api.ts` | Frontend has 356-line API file; admin has 42-line wrapper with `request()` helper | Different abstraction levels; admin should use shared client directly |

---

### MEDIUM PRIORITY

#### 2.1 Backend Router Bloat

| File | Lines | Issue |
|------|-------|-------|
| `backend/app/api/v1/routers/foundations.py` | 626 | Single router handles stored foundations, matching, categorization, translation, profile matching |
| `backend/app/api/v1/routers/profile.py` | 383 | Mixes saved grants CRUD with multi-profile management and legacy `/family` endpoints |
| `backend/app/api/v1/routers/auth.py` | 289 | Handles signup, login, token exchange, Google OAuth stub, logout in one file |

#### 2.2 Frontend Page Complexity

| File | Lines | Issue |
|------|-------|-------|
| `apps/frontend/src/pages/ProfileSetup.tsx` | 611 | Single component handles 5-tab form, geography logic, validation, API calls |
| `apps/frontend/src/pages/GrantDetail.tsx` | 478 | Component handles SEO, JSON-LD, saving, formatting, contact info display |
| `apps/frontend/src/pages/Grants.tsx` | 382 | Infinite scroll, SSR data handling, category extraction, saving logic |

#### 2.3 Pipeline Module Coupling

| Location | Issue |
|----------|-------|
| `backend/app/pipeline/orchestrator.py:1-342` | Orchestrator imports all pipeline stages directly; no interface abstraction |
| `backend/app/pipeline/prompts.py:1-111` | Prompt strings are module-level constants; no versioning or templating system |
| `backend/app/foundation/categorization/categorize_foundations.py` | 548-line monolith handling categorization logic |

#### 2.4 Shared Package Gaps

| Issue | Impact |
|-------|--------|
| `@stipendariet/types` lacks admin-specific types (`Scholarship`, `EnrichmentStatus`, `ActiveJobsSummary`) | Admin defines local types, risking drift |
| `@stipendariet/api-client` is zero-dependency but apps wrap it differently | Frontend uses directly; admin adds `request()` wrapper with 401 handling |
| `@stipendariet/ui` has 49 components but no form primitives (ProfileSetup reimplements form logic) | Duplication of form patterns |

---

### LOW PRIORITY

#### 3.1 Minor Inconsistencies

| Location | Issue |
|----------|-------|
| `backend/app/core/security.py` | Uses both `HTTPException` and custom error classes |
| `apps/frontend/src/contexts/` | `AuthContext` uses `useCallback` extensively; `ProfileContext` does not |
| `backend/app/db/models.py` | All 226 lines in single file; no entity separation |
| `apps/frontend/src/lib/utils.ts` | Only 48 lines but exports text formatting used by 2 pages only |

#### 3.2 Documentation Gaps

| Issue |
|-------|
| No API documentation for admin endpoints (OpenAPI spec exists but not maintained) |
| Frontend `README.md` doesn't explain SSR/SSG flow |
| Backend `AGENTS.md` references `graphify-out/` which doesn't exist |

---

## 2. Target Modular Architecture

### 2.1 Backend Target Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, CORS, router registration ONLY
│   │
│   ├── api/                    # API layer (thin routers)
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── routers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── public/     # Public endpoints
│   │   │   │   │   ├── foundations.py
│   │   │   │   │   ├── grants.py
│   │   │   │   │   ├── applications.py
│   │   │   │   │   ├── profiles.py
│   │   │   │   │   └── auth.py
│   │   │   │   └── admin/      # Admin-only endpoints
│   │   │   │       ├── __init__.py
│   │   │   │       ├── sync.py
│   │   │   │       ├── translation.py
│   │   │   │       ├── enrichment.py
│   │   │   │       ├── categorization.py
│   │   │   │       └── system.py
│   │   │   └── deps.py         # Shared dependencies (get_db, auth)
│   │   │
│   │   ├── services/           # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── foundation_service.py
│   │   │   ├── grant_service.py
│   │   │   ├── profile_service.py
│   │   │   ├── application_service.py
│   │   │   ├── auth_service.py
│   │   │   ├── sync_service.py
│   │   │   ├── translation_service.py
│   │   │   ├── enrichment_service.py
│   │   │   └── embedding_service.py
│   │   │
│   │   ├── repositories/       # Data access layer (replaces crud/)
│   │   │   ├── __init__.py
│   │   │   ├── foundation_repo.py
│   │   │   ├── grant_repo.py
│   │   │   ├── profile_repo.py
│   │   │   ├── application_repo.py
│   │   │   └── user_repo.py
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── database.py     # Engine, SessionLocal, get_db ONLY
│   │   │   ├── models/         # Split by entity
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user.py
│   │   │   │   ├── foundation.py
│   │   │   │   ├── grant.py
│   │   │   │   ├── profile.py
│   │   │   │   ├── application.py
│   │   │   │   └── enrichment.py
│   │   │   └── schemas/        # Pydantic schemas by entity
│   │   │       ├── __init__.py
│   │   │       ├── user.py
│   │   │       ├── foundation.py
│   │   │       └── ...
│   │   │
│   │   ├── pipeline/           # Enrichment pipeline (unchanged structure)
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py
│   │   │   ├── discovery.py
│   │   │   ├── validation.py
│   │   │   ├── crawler.py
│   │   │   ├── extraction.py
│   │   │   ├── service_area.py
│   │   │   └── prompts.py
│   │   │
│   │   ├── foundation/         # External API sync (keep, but remove admin logic)
│   │   │   ├── __init__.py
│   │   │   ├── foundation_api.py
│   │   │   ├── sync_service.py
│   │   │   ├── scheduler.py
│   │   │   ├── task_manager.py
│   │   │   └── categorization/
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   │
│   │   └── workers/
│   │       └── enrichment_worker.py
│   │
│   └── tests/                  # Co-located with source (move from tests/)
│       ├── api/
│       ├── services/
│       ├── repositories/
│       └── pipeline/
```

### 2.2 Frontend Target Structure

```
apps/frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   │
│   ├── app/                    # App-level composition
│   │   ├── router.tsx          # Route definitions
│   │   └── providers.tsx       # Auth, Profile, Query providers
│   │
│   ├── pages/                  # Thin page components (delegate to features)
│   │   ├── HomePage.tsx
│   │   ├── GrantsPage.tsx
│   │   ├── GrantDetailPage.tsx
│   │   ├── MatchingPage.tsx
│   │   ├── GeneratePage.tsx
│   │   ├── ApplicationsPage.tsx
│   │   ├── ProfileSetupPage.tsx
│   │   └── AuthPage.tsx
│   │
│   ├── features/               # Feature modules (new)
│   │   ├── grants/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── services/
│   │   │   └── types.ts
│   │   ├── matching/
│   │   ├── applications/
│   │   ├── profile/
│   │   └── auth/
│   │
│   ├── components/             # Shared UI components (move non-SEO here)
│   │   ├── Layout.tsx
│   │   ├── ProtectedRoute.tsx
│   │   ├── ProfileSwitcher.tsx
│   │   ├── FAQSchema.tsx
│   │   └── SEOHead.tsx
│   │
│   ├── contexts/               # Keep only what's needed for cross-feature state
│   │   ├── AuthContext.tsx
│   │   ├── ProfileContext.tsx
│   │   └── SSRDataContext.tsx
│   │
│   ├── lib/
│   │   ├── api.ts              # Thin wrapper around @stipendariet/api-client
│   │   ├── utils.ts
│   │   ├── prompt-builder.ts
│   │   └── profile-options.ts
│   │
│   ├── hooks/                  # Shared hooks
│   │   ├── use-toast.ts
│   │   └── use-debounce.ts
│   │
│   ├── data/
│   │   └── swedish-regions.ts
│   │
│   └── types/                  # Remove; use @stipendariet/types
│       └── grants.ts           # Re-export only
```

### 2.3 Shared Packages Target

```
packages/
├── types/
│   └── src/
│       ├── index.ts            # Re-exports
│       ├── common.ts           # User, Profile, Grant, Application
│       ├── admin.ts            # Admin-specific types (Scholarship, Jobs, etc.)
│       └── geo.ts              # Swedish geography types
│
├── api-client/
│   └── src/
│       ├── index.ts            # createApiClient factory
│       ├── types.ts            # ApiClientConfig, ApiResponse, ApiError
│       └── helpers.ts          # Token handling, error normalization
│
└── ui/
    └── src/
        ├── components/         # Keep as-is (49 components)
        ├── hooks/
        └── index.ts
```

### 2.4 Layer Responsibilities

| Layer | Responsibility | Examples |
|-------|---------------|----------|
| **Routers** | HTTP concerns only: path params, query validation, response serialization | `GET /grants/:id` → `grantService.getById()` |
| **Services** | Business logic, orchestration, validation | `grantService.getById()` calls repo, applies business rules |
| **Repositories** | Data access only: queries, mutations, no business logic | `grantRepo.findById()`, `grantRepo.listWithFilters()` |
| **Models** | Database schema definitions only | SQLAlchemy models |
| **Schemas** | Request/response validation | Pydantic schemas |

---

## 3. Phased Refactoring Plan

### Phase 1: Backend CRUD Separation (Foundation Only)
**Goal:** Split `crud.py` into entity-specific repositories as proof of concept.

**Scope:**
- Create `backend/app/repositories/` directory
- Extract foundation CRUD from `crud.py` → `foundation_repo.py`
- Update `foundations.py` router to use new repo
- Keep `crud.py` for backward compatibility (deprecated)

**Definition of Done:**
- [ ] `foundation_repo.py` exists with typed methods
- [ ] `foundations.py` router imports from repo, not crud
- [ ] All existing tests pass
- [ ] Deprecation warning added to `crud.get_foundations()`

**Estimated effort:** 1 dev-day

---

### Phase 2: Backend Model Separation
**Goal:** Split `models.py` into entity-specific model files.

**Scope:**
- Create `backend/app/db/models/` directory
- Move each model class to its own file
- Update all imports across codebase
- Re-export from `models/__init__.py` for backward compatibility

**Definition of Done:**
- [ ] Each model in its own file
- [ ] All imports updated (grep-verified)
- [ ] Tests pass
- [ ] Import backward compatibility maintained

**Estimated effort:** 1 dev-day

---

### Phase 3: Backend Service Layer (Foundations)
**Goal:** Introduce service layer between routers and repositories.

**Scope:**
- Create `backend/app/services/foundation_service.py`
- Move business logic from router to service
- Router calls service only

**Definition of Done:**
- [ ] `foundation_service.py` exists
- [ ] Router methods are <20 lines (delegation only)
- [ ] Service is unit-testable (no HTTP imports)
- [ ] Tests pass

**Estimated effort:** 2 dev-days

---

### Phase 4: Frontend Feature Extraction (Grants)
**Goal:** Extract grants feature from pages into `features/grants/`.

**Scope:**
- Create `apps/frontend/src/features/grants/`
- Move grant-related hooks, services, components
- Thin out `GrantsPage.tsx` to feature composition only

**Definition of Done:**
- [ ] `features/grants/` directory exists
- [ ] `GrantsPage.tsx` is <100 lines
- [ ] All tests pass
- [ ] No circular dependencies

**Estimated effort:** 2 dev-days

---

### Phase 5: Admin Type Consolidation
**Goal:** Move admin types to `@stipendariet/types`.

**Scope:**
- Add `admin.ts` to `packages/types/src/`
- Move `Scholarship`, `EnrichmentStatus`, `ActiveJobsSummary` types
- Update admin imports

**Definition of Done:**
- [ ] Types exported from `@stipendariet/types`
- [ ] Admin imports updated
- [ ] No local type definitions in admin
- [ ] Build passes

**Estimated effort:** 0.5 dev-days

---

### Phase 6: Backend Router Reorganization
**Goal:** Separate admin and public routers.

**Scope:**
- Create `backend/app/api/v1/routers/public/` and `admin/`
- Move routers to appropriate directories
- Update `main.py` imports

**Definition of Done:**
- [ ] Routers organized by access level
- [ ] `main.py` imports updated
- [ ] All tests pass
- [ ] OpenAPI tags reflect new structure

**Estimated effort:** 1 dev-day

---

### Phase 7: Frontend Auth Context Unification
**Goal:** Unify auth logic between frontend and admin.

**Scope:**
- Extract token handling to `@stipendariet/api-client`
- Both apps use same auth helper
- Remove duplicate logic

**Definition of Done:**
- [ ] Shared auth helper in api-client
- [ ] Both apps use it
- [ ] No duplicate token logic
- [ ] Tests pass

**Estimated effort:** 1 dev-day

---

### Phase 8: Backend Database Layer Cleanup
**Goal:** Split `database.py` into focused modules.

**Scope:**
- Separate engine creation, session management, table creation
- Move admin user creation to separate module
- Remove ALTER TABLE logic (migrations should handle)

**Definition of Done:**
- [ ] `database.py` is <100 lines
- [ ] Engine, session, creation separated
- [ ] ALTER TABLE logic removed (migrations handle)
- [ ] Tests pass

**Estimated effort:** 2 dev-days

---

### Phase 9: Pipeline Service Abstraction
**Goal:** Add interface abstraction to pipeline stages.

**Scope:**
- Define `PipelineStage` interface
- Refactor stages to implement interface
- Orchestrator uses interface, not concrete classes

**Definition of Done:**
- [ ] Interface defined
- [ ] All stages implement it
- [ ] Orchestrator uses interface
- [ ] Tests pass

**Estimated effort:** 2 dev-days

---

### Phase 10: Frontend Profile Feature Extraction
**Goal:** Extract profile management into `features/profile/`.

**Scope:**
- Create `features/profile/`
- Move ProfileContext logic, ProfileSetup, ProfileSwitcher
- Thin out pages

**Definition of Done:**
- [ ] `features/profile/` exists
- [ ] `ProfileSetup.tsx` is <100 lines
- [ ] Context uses feature services
- [ ] Tests pass

**Estimated effort:** 2 dev-days

---

## 4. What NOT to Change

### 4.1 Working Behavior to Preserve

| Area | What to Keep |
|------|--------------|
| **API Endpoints** | All public endpoint paths and response shapes (frontend depends on them) |
| **Auth Flow** | JWT + ForwardAuth dual auth (admin) works correctly |
| **Foundation ID Format** | `foundation-{foundation_id}` canonical format (issue #19) |
| **Profile Matching** | `use_description` flag for self-description opt-in |
| **SSR/SSG** | Pre-render pipeline for SEO (do not break sitemap generation) |
| **Saved Grants Polymorphism** | `foundation-` / `grant-` prefix pattern |

### 4.2 Conventions Worth Keeping

| Convention | Reason |
|------------|--------|
| Co-located tests (`*.test.tsx`) | Easy to find tests for components |
| `@/` path alias | Standard across frontend apps |
| React Query for server state | Works well; team knows it |
| Pydantic schemas for validation | Clear request/response contracts |
| SQLAlchemy models | Team familiarity; pgvector integration works |

### 4.3 Trade-offs and Risks

| Risk | Mitigation |
|------|------------|
| **Import churn** — Moving files breaks many imports | Use IDE refactoring tools; update in bulk |
| **Circular dependencies** — New structure may create cycles | Enforce layer rules: routers → services → repos → models |
| **Test breakage** — Tests import from old paths | Update tests as part of each phase; don't defer |
| **Backward compatibility** — Old imports may still exist | Keep re-exports in `__init__.py` files with deprecation warnings |
| **Merge conflicts** — Large refactors conflict with feature work | Coordinate with team; refactor on feature branches |

### 4.4 Out of Scope (Explicitly Excluded)

| Item | Reason |
|------|--------|
| Kubernetes/Flux manifests | Infra, not application code |
| Dockerfile optimization | Separate concern |
| Alembic migrations | Already working; don't touch |
| Prompt strings in `prompts.py` | Content, not structure |
| Frontend CSS/Tailwind config | Visual, not architectural |
| LLM model selection | Business logic, not architecture |

---

## Summary

**Top 5 Code Smells to Address First:**
1. **Duplicate `parse_json_field()`** in foundations router (5 min fix)
2. **Monolithic `sync_service.py`** (644 lines) — split by concern
3. **`create_tables()` doing migrations + setup + admin creation** — violates SRP
4. **Direct `fetch()` in Matching.tsx** — bypasses shared API client
5. **`crud.py` handling all entities** — split by entity

**Target Architecture Principles:**
- **Thin routers**: HTTP concerns only
- **Services**: Business logic
- **Repositories**: Data access only
- **Features**: Frontend domain modules
- **Shared types**: Single source of truth

**Phase List (10 phases, each independently shippable):**
1. Backend CRUD separation (foundation only)
2. Backend model separation
3. Backend service layer (foundations)
4. Frontend feature extraction (grants)
5. Admin type consolidation
6. Backend router reorganization
7. Frontend auth unification
8. Backend database layer cleanup
9. Pipeline service abstraction
10. Frontend profile feature extraction

**Estimated total effort:** ~14 dev-days (can run phases in parallel where independent)
