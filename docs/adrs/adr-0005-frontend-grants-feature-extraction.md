# ADR-0005: Frontend Grants Feature Extraction

## Status

Accepted

## Context

`apps/frontend/src/pages/Grants.tsx` had grown to 382 lines, mixing page-level concerns (SEO Helmet, breadcrumbs, FAQ schema) with feature logic: a grants list state machine (search, category filter, pagination, infinite scroll, SSR seeding), a saved-grants toggle with auth guard and toast, and presentational markup. The file violated single-responsibility cohesion — every grants-related change required editing one large page component. The modular refactor plan (Phase 4) called for extracting feature code into `features/grants/` to isolate concerns and enable independent testing/reuse.

## Decision

Extract the grants feature into `apps/frontend/src/features/grants/`:

| File | Responsibility |
|------|----------------|
| `types.ts` | Type re-exports (`Grant`, `GrantsResponse`) and local interfaces (`GrantsQueryParams`, `GrantsFilterState`) |
| `hooks/useGrantsList.ts` | Grants list state machine: search, category filter, pagination, infinite scroll, SSR seeding (extracted verbatim from the original page) |
| `hooks/useSavedGrants.ts` | Saved-grants toggle with auth guard and toast (extracted verbatim) |
| `components/GrantCard.tsx` | Presentational card for a single grant |
| `components/GrantSearchBar.tsx` | Search input + category select |
| `components/GrantsResults.tsx` | Results header, loading/empty states, card grid, load-more button |
| `index.ts` | Barrel export |

The page (`Grants.tsx`) was thinned to 93 lines — composition only. It retains the SEO Helmet block (title, meta, og, canonical, BreadcrumbList JSON-LD), FAQSchema, breadcrumb, page heading, the "Hitta matchande" button, and delegates to `<GrantSearchBar>` and `<GrantsResults>` via the two hooks.

API functions remain in `src/lib/api.ts` to preserve the existing test seam (`api.integration.test.ts`). Hooks import from `api.ts`, not from a newly created service module.

## Consequences

**Positive:**
- Page reduced from 382 → 93 lines (<100 DoD threshold).
- Feature logic is now independently testable, reusable, and navigable.
- No circular dependencies: hooks import `api.ts` (stable); components import hooks/types only; page imports from the barrel.
- All 281 frontend unit tests pass unchanged — behavior is identical (pure refactor).
- SSR behavior preserved: `useGrantsList` still seeds from `SSRDataContext` on the client.
- Type import corrected: `GrantsResponse` now imported from `@stipendariet/types` rather than `@/types/grants`, aligning with the shared package convention.

**Negative:**
- Slightly larger file count for a feature that previously lived in one file; navigation requires knowing the `features/grants/` structure.
- Barrel export adds one indirection layer for imports.

## Implementation Notes

- All Swedish UI strings, aria-labels, and Tailwind classes preserved byte-identically from the original page.
- Unchanged files: `src/lib/api.ts`, `GrantDetail.tsx`, `Generate.tsx`, `Matching.tsx`, `entry-server.tsx`, `App.tsx`, `SSRDataContext.tsx`, `AuthContext.tsx`, `page-metadata.ts`, `types/grants.ts`, and all tests.
- Verification: `pnpm --filter frontend exec vitest run` → 19 files / 281 tests passed; `pnpm exec tsc --noEmit` → clean; code review → [SUCCESS] after fixing an `og:description` typo and the `GrantsResponse` import path; security audit → [SUCCESS], no regressions.

---