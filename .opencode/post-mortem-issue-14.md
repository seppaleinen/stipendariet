## Post-Mortem Analysis: Issue #14 — Change Admin Auth to Authentik ForwardAuth

### Findings

- **ExchangeResponse field mismatch (backend `token` vs frontend `access_token`)** — Insufficient initial research: The dev-architect contract specified `token` in the exchange response, but the existing `TokenResponse` pattern used `access_token`. This wasn't caught until code-review — the architect didn't verify the existing contract pattern against `backend/app/db/schemas.py` (TokenResponse line 39).

- **Missing `ApiError` import in `useAuth.tsx`** — Pipeline gap: No verification step checked that all imported symbols exist. The frontend engineer added `error instanceof ApiError` without the import; only caught in code-review pass 2.

- **`get_admin_user` request parameter default (`request: Request = None`)** — Ambiguous scope: The code-reviewer flagged this as critical (FastAPI injects `Request` for router deps; the default masks missing injection in test overrides). Backend engineer left it unchanged — scope decision wasn't explicit in the contract.

- **Timing attack on `X-Internal-Auth` comparison** — Missing skill/script: No security-lint rule for constant-time secret comparison. The plain `!=` comparison was caught by code-reviewer as a Warning.

- **`X-Internal-Auth` scoped to ALL paths, not just `/api/auth/exchange`** — Miscommunication about scope: The ops security audit found the middleware applied globally, leaking the internal auth token requirement to all routes. Required REWORK to scope it (commit 6b45dc1).

- **Authentik API token invalid → group created via direct PostgreSQL INSERT** — Tooling/environment issue: The authentik API token didn't work; instead of debugging the API, the team used a direct SQL INSERT into the authentik DB. Pragmatic but bypasses API audit trail.

- **Reused existing `authentik-forward-auth` middleware (198d old) instead of creating new** — **Positive finding**: Pipeline gap turned into consistency win. Devops-engineer discovered an existing middleware CRD and reused it, avoiding drift.

- **OCI chart 0.15.7 push blocked (pre-existing CI issue)** — Pipeline gap: Release workflow expects Docker images for commits 3386b73, d407b3c, 6b45dc1 that CI hasn't built. ForwardAuth activation blocked until chart push + Flux reconcile. Independent of #14 but blocks deployment.

- **Split PR pattern: Dev+ops merged in single PR #34; ops secret sharing via `valuesFrom` in fleet-infra (PR #726)** — Documentation: This pattern should be codified for future mixed-domain issues.

- **Security warnings from dev audit**: JWT_SECRET_KEY default "change-me" (deployment task), header trust boundary relies on `request.client.host` (nginx IP in Traefik→nginx→backend chain — ensure proxy IPs managed), X-Forwarded-Groups case-sensitive.

- **Rework discipline maintained**: 2 REWORKs on dev side (ExchangeResponse alignment, ApiError import — both critical, both verified), 1 REWORK on ops side (security scope fix) — all within cap of 2.

### Root Causes

| Category | Explanation |
|----------|-------------|
| **Insufficient initial research** | Dev-architect didn't cross-check `ExchangeResponse` against existing `TokenResponse` schema (line 39 in schemas.py), causing the `token` vs `access_token` mismatch that blocked the pipeline. |
| **Ambiguous or incomplete request** | The `request: Request = None` signature in `get_admin_user` was ambiguous — contract didn't specify whether it should be required or optional, leaving the backend engineer to guess. |
| **Miscommunication about scope** | The ops pipeline initially applied the `X-Internal-Auth` check globally via middleware; the security auditor correctly identified this should be scoped to `/api/auth/exchange` only. The brief didn't explicitly state this boundary. |
| **Missing skill or script** | No automated check for constant-time secret comparison (`hmac.compare_digest`), no secret-rotation reminder for `JWT_SECRET_KEY`, no script to create authentik groups via API (fallback to raw SQL). |
| **Pipeline gap** | No pre-commit/pre-push hook validates `ApiError` imports or shared-type drift between backend schemas and frontend interfaces. The `@stipendariet/types` package exists but wasn't enforced as the single source of truth for `ExchangeResponse` until the second fix cycle. |
| **Tooling / environment issue** | Invalid authentik API token forced a PostgreSQL INSERT workaround. This is an environment configuration drift, not a code issue. |

### Skill / Script Gaps (ranked by impact)

1. **Skill: `shared-contract-validator`** — Enforces that backend response schemas (`backend/app/db/schemas.py`) and frontend interfaces (`@stipendariet/types`) stay in sync. Triggers on any change to `*Response` models. Replaces manual cross-check that missed `token` vs `access_token`. Saves ~30 min per review cycle × every auth-related change.

2. **Script: `authentik-group-manager`** — CLI to create/authentik groups and users via API with proper error handling and retry. Replaces the raw PostgreSQL INSERT workaround (saves ~15 min per group + avoids audit-trail gaps). Frequency: low (new admin groups rarely), but high impact when needed.

3. **Skill: `security-lint-rules`** — Adds `hmac.compare_digest` check for secret comparisons, `datetime.utcnow` deprecation warning, and exact-path-match linting. Replaces manual code-reviewer catches. Runs in CI. Saves ~10 min per security audit × every auth endpoint.

4. **Script: `chart-release-guard`** — Pre-flight check before chart version bump: verifies all referenced Docker images exist in registry, all HelmRelease dependencies are satisfied. Would have caught the OCI chart push blocker before merge. Saves ~1 hr debugging failed Flux reconciles.

5. **Modified agent instruction: `code-reviewer` contract check** — Add explicit verification that all `ExchangeResponse`/`TokenResponse` field names match between backend schemas and `@stipendariet/types`. Already partially addressed by moving `ExchangeResponse` to shared types, but needs enforcement.

6. **Pipeline gap: `pre-deploy-secret-check`** — Before any deployment that uses `INTERNAL_AUTH_TOKEN`, verify the secret is decrypted and non-default in the target environment. Catches the "JWT_SECRET_KEY still change-me" class of issues.

### Suggested Improvements

- **New skill: `shared-contract-validator`** — Name: `shared-contract-validator`. Trigger: on any edit to `backend/app/db/schemas.py` or `packages/types/src/index.ts`. Output: diff report of mismatched response shapes + CI gate.

- **New script: `scripts/authentik-group-manager.sh`** — Location: `scripts/authentik-group-manager.sh`. Wraps authentik API calls with proper auth, retries, and idempotency. Replaces `kubectl exec -it postgresql -- psql -c "INSERT INTO..."`.

- **Modified agent instruction: `dev-architect`** — Add: "Before finalizing contracts, verify all response schemas against existing patterns in `backend/app/db/schemas.py` (e.g., `TokenResponse.access_token`) and ensure shared types in `@stipendariet/types` are the single source of truth."

- **Modified agent instruction: `code-reviewer`** — Add: "Verify `ExchangeResponse` field names match `@stipendariet/types` exactly. Flag any `token` vs `access_token` drift as Critical."

- **Pipeline gap: Secret rotation reminder** — Add a scheduled task or pre-deploy check that warns if `JWT_SECRET_KEY` equals default `change-me` in any environment.

### Recommended Follow-ups

- **Issue 1:** Create issue to fix CI workflow (build Docker images for commits 3386b73, d407b3c, 6b45dc1 → push chart 0.15.7 → Flux reconcile). This unblocks ForwardAuth activation.

- **Issue 2:** Track JWT_SECRET_KEY rotation as deployment task (remove default "change-me" in production).

- **Issue 3:** Create issue: "Migrate adminToken to httpOnly cookie" (XSS risk noted in security audit — token currently in localStorage).

- **Issue 4:** Create skill `shared-contract-validator` to prevent backend/frontend schema drift.

- **Issue 5:** Create script `authentik-group-manager` for reliable authentik group/user management via API.

- **Issue 6:** Add `hmac.compare_digest` lint rule to CI (security-lint skill extension).

- **Issue 7:** Document the "split PR pattern" (dev+ops in single app-repo PR, infra secrets via `valuesFrom` in fleet-infra) as a convention for future mixed-domain issues.

---

**STATUS:** `[SUCCESS]`
**REWORK_COUNT:** `0` | **KILLED_BY_RESTART:** `0`

**SUMMARY:** Post-mortem of Issue #14 identifies ForwardAuth activation blocked on OCI chart push (pre-existing CI issue), security warnings on JWT secret and header trust boundary, and successful rework discipline across both pipelines (3 REWORKs total, all within cap). Key wins: reuse of existing 198-day-old authentik middleware; shared-type migration for ExchangeResponse. Root causes cluster around insufficient upfront contract verification, missing automated security checks, and an environment-specific authentik API token failure.

**RATIONALE:** The analysis traces each finding to its root cause category with evidence from the session exports and git history. Skill/script gaps are ranked by estimated time saved × frequency. The recommendations are concrete and actionable — each maps to a specific file, skill name, or script path.

**TRACE:** team-lead → post-mortem-analyst [SUCCESS]