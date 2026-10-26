# PR #34: Admin Auth via Authentik ForwardAuth

## Summary

Replace homemade admin password login with Authentik ForwardAuth for centralized identity management and improved security.

## Changes

### Stipendariet Repo
- **kubernetes/charts/stipendiatet/admin-frontend/templates/ingress.yaml**: Added Traefik middleware annotation `traefik.ingress.kubernetes.io/router.middlewares: traefik-authentik-forward-auth@kubernetescrd`
- **kubernetes/charts/stipendiatet/admin-frontend/templates/environment-secrets.yaml**: Added `INTERNAL_AUTH_TOKEN` env var from Helm values
- **kubernetes/charts/stipendiatet/admin-frontend/values.yaml**: Added `env.internalAuthToken: ""` default
- **kubernetes/charts/stipendiatet/admin-frontend/Chart.yaml**: Bumped version 0.15.6 → 0.15.7
- **apps/admin/nginx.conf**:
  - Added `env INTERNAL_AUTH_TOKEN;` directive
  - Added ForwardAuth header passthrough (`X-Forwarded-User`, `X-Forwarded-Email`, `X-Forwarded-Groups`)
  - Scoped `X-Internal-Auth` to `/api/auth/exchange` endpoint only (security fix from `ai-security-auditor` review)

### Fleet-infra Repo
- **flux/stipendiatet/admin-frontend/helmrelease.yaml**: Added `valuesFrom` referencing `backend-secrets` to inject `internalAuthToken`

### Backend (see backend PR for full details)
- New `POST /api/auth/exchange` endpoint with tokenless ForwardAuth validation
- `_validate_forwardauth()` and `_is_internal_request()` security helpers
- Auto-provisioning of admin users with `hashed_password=None`

### Admin Frontend
- `useAuth.tsx` replaces password login with ForwardAuth exchange flow
- `LoginPage.tsx` shows spinner during exchange with "Continue with Authentik" fallback
- Proactive token refresh (<5 min before expiry, 60s interval)

## Testing

- 25 backend tests + 7 admin hook tests pass
- Manual verification: admin users in `stipendariet-admins` Authentik group can access admin panel
- Emergency fallback: existing `POST /api/auth/login` remains functional

## Breaking Changes

- Admin frontend no longer displays password login form by default
- `ADMIN_PASSWORD` env var optional (only needed for emergency fallback)
- Requires Authentik ForwardAuth middleware configured in Traefik

## Related

- ADR: `docs/ADR-0003-admin-auth-authentik-forwardauth.md`
- Fleet-infra PR: #726
- GitHub Issue: #14
