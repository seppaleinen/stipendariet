# Admin Auth via Authentik ForwardAuth

## Summary

Replace the homemade email/password admin login with Authentik ForwardAuth. New `POST /api/auth/exchange` endpoint validates ForwardAuth headers behind an internal auth token and network boundary, auto-provisions admin users, and returns an HS256 JWT. Frontend login flow updated to use ForwardAuth exchange with proactive token refresh.

## Changes

- **Backend (`backend/app/api/v1/routers/auth.py`)**: Added `POST /api/auth/exchange` tokenless endpoint that trusts `X-Forwarded-Email`, `X-Forwarded-User`, `X-Forwarded-Groups` headers only when `X-Internal-Auth` matches `INTERNAL_AUTH_TOKEN` (constant-time compare) and `request.client.host` is in `INTERNAL_NETWORKS` CIDR list. Auto-provisions admin User with `hashed_password=None`.
- **Backend (`backend/app/core/security.py`)**: Added `_is_internal_request` (pre-compiled CIDR check) and `_validate_forwardauth` (validates internal token → network → admin group → email). Updated `get_admin_user` to fall back to ForwardAuth validation ONLY on `/api/auth/exchange` path; JWT flow unchanged for all other routes.
- **Backend (`backend/app/core/config.py`)**: Added `INTERNAL_NETWORKS`, `INTERNAL_AUTH_TOKEN`, `AUTHENTIK_ADMIN_GROUP` settings with sensible defaults.
- **Admin frontend (`apps/admin/src/hooks/useAuth.tsx`)**: Removed password `login`; added `exchange()`, `refreshToken()`, `isExchanging`; auto-exchange on mount if no valid token in `localStorage.adminToken`; proactive refresh <5 min before expiry (60s interval); logout optionally honors `VITE_AUTHENTIK_LOGOUT_URL`.
- **Admin frontend (`apps/admin/src/lib/api.ts`)**: Added `apiPublic` tokenless client for `/auth/exchange` call.
- **Shared (`packages/types/src/index.ts`)**: Added `ExchangeResponse` interface shared between backend and frontend.
- **Tests**: `backend/tests/test_auth_exchange.py` (25 tests green); `apps/admin/src/hooks/useAuth.test.tsx` (7 tests green); updated LoginPage tests.

## Testing

- Backend: `pytest tests/test_auth_exchange.py` — 25 passed, 6 skipped. Covers header validation, internal network IP check, admin group membership, auto-provisioning, and JWT minting.
- Admin frontend: `pnpm --filter admin exec vitest run src/hooks/useAuth.test.tsx` — 7 passed. Covers auto-exchange, refresh threshold, periodic refresh, and logout behavior.
- All existing tests remain green: backend 322 passed/6 skipped; admin 57 passed.

## Breaking Changes

None. Existing `POST /api/auth/login` password endpoint kept as emergency fallback. Frontend user JWT flow untouched. New `apiPublic` client is opt-in for the exchange call.

## Ops Prerequisites

- Traefik ForwardAuth middleware must inject `X-Internal-Auth`, `X-Forwarded-User`, `X-Forwarded-Email`, `X-Forwarded-Groups` on the admin ingress.
- Admin nginx must pass those headers through to the backend.
- Authentik application `stipendariet-admin` + group `stipendariet-admins` must exist and be configured.

## Deployment Notes

- **JWT_SECRET_KEY**: Rotate from default `change-me` before production deployment. Set via `JWT_SECRET_KEY` env var.
- **Header trust boundary**: Backend only validates ForwardAuth headers when request originates from trusted internal networks (`INTERNAL_NETWORKS`). External exposure of `X-Internal-Auth` enables header spoofing; ensure Traefik/admins are not publicly exposed.
- If `VITE_AUTHENTIK_LOGOUT_URL` is set, logout redirects to Authentik; otherwise falls back to `/login`.
- Backward compatibility: password login at `/api/auth/login` remains functional for emergency access.