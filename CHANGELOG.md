# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Admin auth via Authentik ForwardAuth**: `POST /api/auth/exchange` endpoint auto-provisions admin users and returns HS256 JWT; `useAuth.tsx` replaces password login with ForwardAuth exchange; `LoginPage.tsx` shows spinner and "Continue with Authentik" fallback; `ExchangeResponse` interface added to `@stipendariet/types`.

### Changed
- **Backend**: `_validate_forwardauth` and `_is_internal_request` in `backend/app/core/security.py` enforce header trust boundary (internal auth token + CIDR network check); `get_admin_user` falls back to ForwardAuth only on `/api/auth/exchange` path.
- **Frontend**: `useAuth.tsx` removes password login; new `exchange()`, `refreshToken()`, `isExchanging` states; auto-exchange on mount; proactive refresh <5 min before expiry. `ProtectedRoute.tsx` shows loading spinner during exchange. `apiPublic` tokenless client added for exchange call.

### Fixed
- None

### Removed
- Password login form from admin `LoginPage.tsx`; `ADMIN_PASSWORD` env var no longer required for ForwardAuth flow.

---
*This changelog follows the standard [Keep a Changelog](https://keepachangelog.com/) format.*