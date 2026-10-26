# Operations Runbook: Authentik ForwardAuth for Admin Panel

## Overview

The stipendariet admin panel (`stipendieadmin.labb.site`) uses Authentik ForwardAuth for authentication. This document covers verification, user management, and troubleshooting for ops teams.

## Architecture

```
User → Traefik (Ingress) → ForwardAuth Middleware → Authentik
                                        ↓
                            Nginx (admin-frontend) → Backend (/api/auth/exchange)
```

Traefik injects headers (`X-Forwarded-User`, `X-Forwarded-Email`, `X-Forwarded-Groups`) after Authentik authenticates the user. Nginx passes these to the backend. The backend validates them at `/api/auth/exchange` using:
1. `X-Internal-Auth` header matching `INTERNAL_AUTH_TOKEN` (constant-time)
2. Request IP in `INTERNAL_NETWORKS` CIDR list
3. User in `stipendariet-admins` group via `X-Forwarded-Groups`
4. `X-Forwarded-Email` present

## Verify Middleware is Working

### 1. Check Ingress Annotation
```bash
kubectl get ingress -n stipendiatet admin-frontend -o yaml | grep -A2 middlewares
# Should show: traefik-authentik-forward-auth@kubernetescrd
```

### 2. Verify Traefik Middleware CRD
```bash
kubectl get middleware -A | grep authentik
# Should show traefik-authentik-forward-auth in traefik namespace
```

### 3. Test Header Injection
```bash
# From inside cluster (e.g., via kubectl exec into a pod)
curl -H "Host: stipendieadmin.labb.site" http://traefik.traefik.svc.cluster.local/api/auth/exchange -v
# Check response headers show X-Forwarded-* headers
```

### 4. Verify Nginx Config
```bash
kubectl exec -n stipendiatet deploy/admin-frontend -- cat /etc/nginx/nginx.conf | grep -A5 "X-Internal-Auth"
# Should show X-Internal-Auth only in /api/auth/exchange location block
```

### 5. Check Secret Injection
```bash
kubectl get secret -n stipendiatet admin-frontend-env-secrets -o yaml
# INTERNAL_AUTH_TOKEN should be populated (base64 decoded)
```

## Add Users to `stipendariet-admins` Group

### Via Authentik UI
1. Log into Authentik admin (`authentik.labb.site/if/admin/`)
2. Navigate to **Directory → Groups**
3. Find `stipendariet-admins` (group ID: 1)
4. Add users via **Members** tab

### Via PostgreSQL (Direct)
```bash
# Connect to Authentik PostgreSQL
kubectl exec -n authentik postgresql-0 -- psql -U authentik -d authentik

# Add user to group (replace USER_ID)
INSERT INTO "authentik_core_group"."authentik_core_user_groups" ("group_id", "user_id")
VALUES (1, 'USER_ID');
```

### Verify Membership
```bash
# Check user's groups in Authentik
# Or test via API with user's session
```

## Token Management

### Rotate INTERNAL_AUTH_TOKEN
1. Generate new token:
   ```bash
   openssl rand -base64 32
   ```
2. Update in fleet-infra `backend-secrets`:
   ```yaml
   # flux/stipendiatet/backend-secrets.yaml (or equivalent secret)
   internalAuthToken: <new-token>
   ```
3. Apply and restart admin-frontend:
   ```bash
   flux reconcile kustomization stipendiatet -n flux-system
   kubectl rollout restart deployment/admin-frontend -n stipendiatet
   ```

## Troubleshooting

### Auth Fails with 401/403

| Symptom | Check |
|---------|-------|
| 401 "Invalid internal auth token" | `INTERNAL_AUTH_TOKEN` mismatch between fleet-infra secret and nginx env var |
| 401 "Request not from trusted proxy" | Backend `INTERNAL_NETWORKS` CIDR doesn't match Traefik/Nginx egress IP |
| 403 "Admin group membership required" | User not in `stipendariet-admins` group; check `X-Forwarded-Groups` header |
| 401 "X-Forwarded-Email required" | Authentik ForwardAuth not configured to pass email; check provider config |

### Debug Header Flow
```bash
# Add temporary debug location to nginx.conf (requires rebuild)
location /debug-headers {
    return 200 "User: $http_x_forwarded_user\nEmail: $http_x_forwarded_email\nGroups: $http_x_forwarded_groups\nInternal: $http_x_internal_auth\n";
}

# Test from cluster
curl http://admin-frontend/debug-headers
```

### Backend Logs
```bash
kubectl logs -n stipendiatet deploy/backend -f | grep -E "(ForwardAuth|_validate_forwardauth|_is_internal_request)"
# Look for validation failures
```

### Traefik ForwardAuth Logs
```bash
kubectl logs -n traefik deploy/traefik -f | grep -i forwardauth
# Check middleware connectivity to Authentik
```

### Common Issues

1. **Headers missing**: Traefik ForwardAuth middleware not attached to ingress or Authentik provider misconfigured
2. **Token mismatch**: `INTERNAL_AUTH_TOKEN` in fleet-infra secret differs from what nginx receives
3. **IP not in CIDR**: Backend `INTERNAL_NETWORKS` doesn't include Traefik/Nginx pod IPs (check `settings.INTERNAL_NETWORKS` in backend config)
4. **Group name mismatch**: Authentik group name must exactly match `AUTHENTIK_ADMIN_GROUP` setting (default: `stipendariet-admins`)

## Emergency Access

If ForwardAuth is unavailable, admin users can still use the emergency password login:
- Endpoint: `POST /api/auth/login`
- Requires: `ADMIN_USERNAME` and `ADMIN_PASSWORD` env vars in backend
- Only works if JWT authentication is attempted first (falls through on invalid/expired JWT)

## References

- ADR: `docs/ADR-0003-admin-auth-authentik-forwardauth.md`
- PR: stipendariet #34, fleet-infra #726
- GitHub Issue: #14
- Backend security: `backend/app/core/security.py` (`_validate_forwardauth`, `_is_internal_request`)