# ADR-0006: Admin Types Consolidation into @stipendariet/types

## Status

Accepted

## Context

The admin panel (`apps/admin`) previously defined its own types in `apps/admin/src/types/index.ts`, including `Scholarship`, `ScholarshipQueueItem`, `EnrichmentStatus`, and `ActiveJobsSummary`. This created several problems:

1. **Type drift risk** — Admin types were not validated against backend API contracts
2. **Duplication** — `User` type was re-exported from `@stipendariet/types` but admin types lived locally
3. **Inconsistent ownership** — Frontend used `@stipendariet/types`; admin had a split dependency model
4. **Orphaned feature blindness** — The `Scholarship` type mapped to a `scholarships` table dropped in alembic migration `b64ec2432846` with no corresponding backend routes, but this was not documented in the type definition

The modular refactoring plan (Phase 5) called for moving all admin types into the shared `@stipendariet/types` package.

## Decision

Create `packages/types/src/admin.ts` as a dedicated submodule exporting 8 admin-specific types:

- `Scholarship` — **ORPHANED FEATURE**: backend table dropped, no routes exist, admin UI will 404
- `ScholarshipQueueItem` — **ORPHANED FEATURE**: same orphaned status
- `FoundationStats` — Aggregated enrichment statistics
- `EnrichmentStats` — Enrichment progress summary (renamed from `EnrichmentStatus` to avoid collision with backend `EnrichmentStatus` enum)
- `ActiveJob` — Active Celery task reference
- `ActiveJobsSummary` — Map of job names to active tasks
- `FoundationSearchResult` — Foundation lookup result
- `EnrichmentDefaults` — Default prompts/model config for enrichment jobs

Update `packages/types/src/index.ts` to re-export from `./admin`.

Delete `apps/admin/src/types/index.ts`.

Trim `apps/admin/src/types/jobs.ts` to UI-state types only (`ActionState`, `JobProgressState`).

Update all 13 admin consumer files to import from `@stipendariet/types`.

Add JSDoc to all 8 types with explicit orphaned-feature notices where applicable.

## Consequences

### Positive

- **Single source of truth** — All shared types now live in `@stipendariet/types`; both frontend and admin consume from same package
- **Orphaned types documented** — JSDoc warnings on `Scholarship` and `ScholarshipQueueItem` make the dead contract explicit; prevents future developers from treating them as live APIs
- **Naming collision avoided** — Renamed `EnrichmentStatus` → `EnrichmentStats` to distinguish from backend `EnrichmentStatus` enum
- **Dead code removed** — `EnrichmentDetail` type (zero consumers) deleted
- **Build verified** — `@stipendariet/types` builds cleanly; admin app builds and all 50 tests pass

### Negative

- **Orphaned types still compile** — `Scholarship`/`ScholarshipQueueItem` remain in the shared package to avoid breaking admin build; they must be removed when the orphaned feature is formally retired
- **Admin now depends on shared types for everything** — Minor coupling increase, but this was the intended architecture