# ADR-0003: Admin Auth via Authentik ForwardAuth

## Status

Accepted

## Context

The stipendariet admin panel previously used a homemade email/password login system. This ADR addresses the need to replace that system with Authentik ForwardAuth for improved security and centralized identity management. The admin panel must authenticate users through Authentik while maintaining backward compatibility with emergency password login.

## Decision

Implement a tokenless `POST /api/auth/exchange` endpoint in the Python backend that trusts Authentik ForwardAuth identity headers (`X-Forwarded-Email`, `X-Forwarded-User`, `X-Forwarded-Groups`) only when:

1. `X-Internal-Auth` header matches `settings.INTERNAL_AUTH_TOKEN` via constant-time comparison (`hmac.compare_digest`), and
2. The TCP peer (`request.client.host`) is in the `INTERNAL_NETWORKS` CIDR list.

Auto-provision the admin User in DB with `hashed_password=None` (ForwardAuth-only identity), mint an HS256 admin JWT, and return `{ access_token, token_type: "bearer", expires_in }`.

Backend security helper `_validate_forwardauth` validates the header chain in order: internal auth token → internal network IP check → admin group membership from `X-Forwarded-Groups` → required `X-Forwarded-Email`. New helper `_is_internal_request` uses pre-compiled `ipaddress.ip_network` objects for performance.

Admin frontend (`apps/admin/`) replaces password login with ForwardAuth exchange flow: `useAuth.tsx` auto-exchanges on mount, proactive refresh <5 min before expiry (60s interval), optional `VITE_AUTHENTIK_LOGOUT_URL` support. `LoginPage.tsx` shows spinner while exchanging and "Continue with Authentik" fallback. `ProtectedRoute.tsx` shows loading spinner while `isLoading || isExchanging`.

Existing `POST /api/auth/login` kept as emergency fallback; existing frontend user JWT flow untouched.

## Consequences

Positive:
- Centralized identity via Authentik eliminates custom password storage for admins.
- Tokenless exchange reduces attack surface; credentials never transmitted to backend.
- Auto-provisioning ensures new admins are instantly operable without DB migration.
- CI test coverage: 25 backend tests + 7 admin hook tests all green.

Negative:
- Deployment requires Traefik ForwardAuth middleware injecting required headers.
- Backend must only trust headers from internal proxy chain; external exposure of `X-Internal-Auth` enables spoofing.
- Rotate `JWT_SECRET_KEY` from default `change-me` before production.
- Network topology must ensure admin ingress passes headers through to backend.

---