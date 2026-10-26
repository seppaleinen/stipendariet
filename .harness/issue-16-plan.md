# Plan — Issue #16: Use Self-description in application generation (opt-in)

Status: PROPOSED (awaiting user approval)
Date: 2026-10-25
Issue: https://github.com/seppaleinen/stipendariet/issues/16
Predecessor: #15 (close comment: "Deferred by design: opt-in use of self-description in application generation")

## Problem

`buildApplicationPrompt(profile, foundation)` (apps/frontend/src/lib/prompt-builder.ts) draws
exclusively on structured profile selections and ignores `profile.self_description`.
Users who write their situation in their own words get nothing from it at generation time.

## Grounded findings (verified against code 2026-10-25)

1. `apps/frontend/src/lib/prompt-builder.ts:31` — `buildApplicationPrompt` never reads
   `profile.selfDescription`. Prompt is built fully client-side.
2. `apps/frontend/src/pages/Generate.tsx:56` — single call site; passes `(activeProfile, foundation)`.
3. Backend needs nothing: `backend/app/api/v1/routers/foundation_sync.py:84-113` —
   `GenerationRequest { prompt: str }` proxies the prompt string to LiteLLM (`gemma-4-12b`).
   No schema, migration, or router change.
4. Length guarantee already exists end-to-end: zod `max(2000)` (ProfileSetup.tsx:60) +
   pydantic `max_length=2000` (backend schemas.py:87) + `maxLength={2000}` on the textarea.
5. The #15 "Matching source toggle" referenced in the issue is not a live UI pattern:
   `findMatchingFoundationsByProfile` (api.ts:319, the wrapper carrying `useDescription`)
   has zero call sites; Matching.tsx does a raw free-text fetch to `/foundations/matching`.
6. `CONTEXT.md:54` currently states the invariant this feature deliberately changes:
   "The Self-description drives Finding only — it never feeds application generation,
   which consumes Structured selections only."

## Design decisions (recommendations)

### D1 — Opt-in mechanism: checkbox in the Generate UI
A single checkbox ("Använd min egen beskrivning") in the Generate page profile card,
adjacent to the Generate button. Ephemeral local state, default OFF.
- Rationale: generation is a one-shot action page, not list browsing; the matching
  source-toggle pattern doesn't exist in current UI to mirror; default OFF satisfies
  "Structured-only behavior unchanged by default".
- Rejected: profile-level persisted setting — wrong scope (choice is per-generation
  context, not an attribute of the profile); mirroring the matching toggle — dead pattern.

### D2 — Prompt budget: verbatim, hard-capped at 2000 chars in the builder
Include the description verbatim; the builder defensively truncates at 2000 chars
(belt-and-braces — the DB/UI caps should make truncation a no-op, but the builder's
contract must not depend on upstream validation).
- Rationale: 2000 chars ≈ 500 tokens vs a 12B model — free. Summarizing would add an
  LLM round-trip, latency, cost, and would distort "their own words shape the output".
- Rejected: summarize-first (cost/latency, defeats the purpose); hard-truncate shorter
  (arbitrary — the field cap already bounds it).

### D3 — Interaction with structured selections: ADDITIVE, not either/or
When opted in AND description non-empty, append a "Självbeskrivning" section after the
structured profile section. Structured selections are never dropped or replaced.
- Rationale: matching's either/or semantics are forced by embedding mechanics (one text
  is embedded); a prompt build has no such constraint. The self-description is additional
  context about the same person, not an alternative representation. Either/or would make
  generation strictly worse for users who filled both.
- Rejected: either/or (drops valuable structured facts; solves a non-problem here).

### D4 — Language: output stays Swedish regardless of description language
One instruction line added to the prompt when the section is included: the applicant's
own description may be in another language; write the application in Swedish regardless.
Multilingual embeddings remain out of scope (no embeddings involved in generation).

## Changes

1. `apps/frontend/src/lib/prompt-builder.ts`
   - Extend signature: `buildApplicationPrompt(profile, foundation, options?: { useSelfDescription?: boolean })`.
     Default (options omitted) → byte-identical output to today.
   - New exported helper `truncateDescription(text: string, max = 2000): string`
     (trims, hard-caps with ellipsis) — unit-testable seam.
   - When opted in and `selfDescription` non-empty after trim: append
     `- Självbeskrivning (sökändens egna ord):\n<text>\n` after the structured profile
     lines, plus the D4 Swedish-output instruction line.
2. `apps/frontend/src/lib/prompt-builder.test.ts`
   - default excludes description (regression: structured-only output unchanged)
   - opt-in includes verbatim description
   - >2000 chars truncated to cap (bounded prompt regardless of length)
   - opt-in with empty/whitespace description → section omitted (no dangling header)
   - foundation context unaffected in both modes
3. `apps/frontend/src/pages/Generate.tsx`
   - Checkbox (Radix-based `@stipendariet/ui`) with Swedish label "Använd min egen beskrivning";
     helper text explains it adds the profile's Egen beskrivning to the application.
   - Disabled + hint with link to /profile-setup when active profile has no description.
   - State passed to `buildApplicationPrompt(activeProfile, foundation, { useSelfDescription })`.
4. `CONTEXT.md`
   - Amend the Domain Rules invariant: Self-description feeds application generation
     only on explicit per-generation opt-in; default remains Structured-only.

## Explicitly out of scope
- Backend (schema, migration, router) — none needed.
- Persisting the opt-in choice (profile-level setting) — future need, not now.
- Matching page / embedding changes — untouched.
- Multilingual embeddings (deferred from #15).

## Acceptance (maps to issue)
- [ ] User can choose whether Self-description informs generation (checkbox, default off)
- [ ] Prompt size bounded regardless of description length (builder-level 2000-char cap)
- [ ] Structured-only behavior unchanged by default (byte-identical prompt without opt-in)

## Verification plan
- `pnpm --filter @stipendariet/frontend exec vitest run src/lib/prompt-builder.test.ts`
- Full frontend vitest suite + `turbo run build` green; ruff untouched (no backend change).
- Manual: Generate page renders checkbox; with description → prompt includes section;
  without → disabled with hint.

## Dispatch
On approval: `team-lead → dev-team-lead` (full dev pipeline: design → implement → verify),
brief = this file. Verification via code-reviewer; security audit per pipeline defaults.
