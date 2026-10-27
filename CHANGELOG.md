# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Admin auth via Authentik ForwardAuth**: `POST /api/auth/exchange` endpoint auto-provisions admin users and returns HS256 JWT; `useAuth.tsx` replaces password login with ForwardAuth exchange; `LoginPage.tsx` shows spinner and "Continue with Authentik" fallback; `ExchangeResponse` interface added to `@stipendariet/types`.
- **Ops: Authentik ForwardAuth deployment**: Traefik middleware annotation on admin ingress; `INTERNAL_AUTH_TOKEN` via Helm values and fleet-infra `backend-secrets`; nginx header passthrough for `X-Forwarded-User/Email/Groups`; `X-Internal-Auth` scoped to `/api/auth/exchange` only.

### Changed
- **Frontend (Grants feature)**: Restructured the grants feature into `apps/frontend/src/features/grants/` with dedicated hooks (`useGrantsList`, `useSavedGrants`) and presentational components (`GrantCard`, `GrantSearchBar`, `GrantsResults`). The page itself is now a thin composition layer (382 → 93 lines). No behavior or UI changes — pure refactor (#35, Phase 4).
- **Backend (modular refactor)**: Extracted `FoundationRepository` (`app/repositories/`), split `app/db/models.py` into entity-specific files, and introduced `FoundationService` so the foundations router delegates business logic to a service layer (#35, Phases 1-3). Public API unchanged.
- **Backend**: `_validate_forwardauth` and `_is_internal_request` in `backend/app/core/security.py` enforce header trust boundary (internal auth token + CIDR network check); `get_admin_user` falls back to ForwardAuth only on `/api/auth/exchange` path.
- **Frontend**: `useAuth.tsx` removes password login; new `exchange()`, `refreshToken()`, `isExchanging` states; auto-exchange on mount; proactive refresh <5 min before expiry. `ProtectedRoute.tsx` shows loading spinner during exchange. `apiPublic` tokenless client added for exchange call.

### Fixed
- None

### Removed
- Password login form from admin `LoginPage.tsx`; `ADMIN_PASSWORD` env var no longer required for ForwardAuth flow.

---
*This changelog follows the standard [Keep a Changelog](https://keepachangelog.com/) format.*