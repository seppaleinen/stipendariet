## Summary
Deliver `SEARXNG_URL` via the chart's `envFrom` Secret instead of a kustomize postRenderer patch. Pulls in chart 0.15.15, which renders the exact underscore-preserved `SEARXNG_URL` name the backend reads.

## Changes
- `flux/stipendiatet/backend/helmrelease.yaml`: add `env.searxngUrl: "http://searxng-http.searxng.svc.cluster.local:8080"` plaintext under `values:`; remove the `SEARXNG_URL` postRenderer patch and stale comments; keep the two `LITELLM_API_KEY` secretKeyRef postRenderer patches.
- `flux/sources/oci-repositories.yaml`: bump backend OCIRepository `ref.semver` 0.15.14 → 0.15.15.

(Chart source: `kubernetes/charts/stipendiatet/backend/templates/environment-secrets.yaml` now emits `SEARXNG_URL: {{ .Values.env.searxngUrl | quote }}` in the backend-env-secrets stringData Secret — sipendariet commit a554b7a, chart 0.15.15.)

## Why
The backend reads `SEARXNG_URL` (underscore) from `backend/app/core/config.py`. The chart's `upper | replace "_" "-"` transform emitted `SEARXNG-URL` (hyphen), so the app never saw the var and it had to be force-injected via a postRenderer patch. The chart now emits `SEARXNG_URL` verbatim (stipendariet chart 0.15.15), eliminating the hack.

## Verification
- HelmRelease reconciled to chart 0.15.15; backend pod Running/Ready.
- `SEARXNG_URL=http://searxng-http.searxng.svc.cluster.local:8080` present via envFrom (not postRenderer).
- searxng-http reachable (HTTP 429 rate-limit expected on public anonymous `/search`).
- `LITELLM_API_KEY` still injected via secretKeyRef.

## Security
`SEARXNG_URL` is a non-secret cluster URL; `LITELLM_API_KEY` remains a Sops-encrypted secretKeyRef; no plaintext credentials; OCI pinned, no downgrade race.

Merge SHA: 9d9dae8574c9bcddebd58079ef345a3f35074209
