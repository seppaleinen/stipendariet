# PR #35 — Frontend Grants Feature Extraction (Phase 4)

## Summary

Pure refactor: extract the grants feature from `apps/frontend/src/pages/Grants.tsx` into `apps/frontend/src/features/grants/`, thinning the page to composition only. No behavior change.

## Changes

**Created** — `apps/frontend/src/features/grants/`:
- `types.ts` — type re-exports and local interfaces (`GrantsQueryParams`, `GrantsFilterState`)
- `hooks/useGrantsList.ts` — grants list state machine (search, category filter, pagination, infinite scroll, SSR seeding)
- `hooks/useSavedGrants.ts` — saved-grants toggle with auth guard and toast
- `components/GrantCard.tsx` — presentational card for a single grant
- `components/GrantSearchBar.tsx` — search input + category select
- `components/GrantsResults.tsx` — results header, loading/empty states, card grid, load-more button
- `index.ts` — barrel export

**Modified** — `apps/frontend/src/pages/Grants.tsx`:
- Reduced from 382 → 93 lines
- Retains SEO Helmet, FAQSchema, breadcrumb, page heading, "Hitta matchande" button
- Composes `<GrantSearchBar>` and `<GrantsResults>` via `useGrantsList` and `useSavedGrants`

**Unchanged** — `src/lib/api.ts`, `GrantDetail.tsx`, `Generate.tsx`, `Matching.tsx`, `entry-server.tsx`, `App.tsx`, `SSRDataContext.tsx`, `AuthContext.tsx`, `page-metadata.ts`, `types/grants.ts`, and all tests.

## Definition of Done

- [x] `features/grants/` directory exists with hooks, components, types, and barrel export
- [x] `Grants.tsx` is <100 lines (93)
- [x] All tests pass (281/281)
- [x] No circular dependencies
- [x] `tsc --noEmit` clean
- [x] Code review approved (after fixing `og:description` typo and `GrantsResponse` import path)
- [x] Security audit — no regressions

## Test Results

- `pnpm --filter frontend exec vitest run` → **Test Files 19 passed (19), Tests 281 passed (281)**
- `pnpm exec tsc --noEmit` → clean
- `wc -l apps/frontend/src/pages/Grants.tsx` → 93

## Breaking Changes

None — pure refactor, behavior identical.

## Related

- Phase 4 of the modular refactor plan (`.harness/research-brief-modular-refactor.md` lines 385-400)
- ADR-0005: Frontend Grants Feature Extraction