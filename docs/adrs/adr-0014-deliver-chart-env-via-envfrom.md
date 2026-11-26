# Deliver Chart Env via envFrom Secret

Status: Accepted

## Context
The backend reads `SEARXNG_URL` (exact underscore name) from `backend/app/core/config.py`. A chart template rendered env names via `upper | replace "_" "-"`, producing `SEARXNG-URL` (hyphen) — a mismatch that left the var undefined in the app. To work around it, fleet-infra force-injected `SEARXNG_URL` with a kustomize postRenderer patch on the backend HelmRelease. This was fragile and version-sensitive.

## Decision
Deliver chart-provided env vars through the chart's `envFrom` Secret rather than kustomize postRenderer patches. The chart renders env names verbatim (underscore preserved). Populate the envFrom Secret slot from `values:` in the HelmRelease (stipendariet chart 0.15.15, which emits `SEARXNG_URL: {{ .Values.env.searxngUrl | quote }}`).

Keep `secretKeyRef` postRenderer patches only for secrets that originate outside the chart (e.g. `LITELLM_API_KEY` via a Sops-encrypted Flux Secret).

## Consequences
- Positive: single source of truth for env names; no postRenderer fragility; names the app reads are emitted exactly.
- Negative: requires chart versions to be bumped and pinned in the GitOps OCIRepository when env naming changes (ref.semver bump in `flux/sources/oci-repositories.yaml`).
- Rule: prefer `envFrom` over postRenderer patches for any env a chart provides. Reserve postRenderer patches for secrets or values that must be injected from outside the chart.

## Evidence
- Chart 0.15.15 emits `SEARXNG_URL` verbatim in `templates/environment-secrets.yaml` stringData.
- fleet-infra HelmRelease added `env.searxngUrl` plaintext under `values:`; removed the postRenderer patch.
- Verified on cluster: backend Running/Ready, `SEARXNG_URL` present via envFrom, searxng-http reachable, `LITELLM_API_KEY` still injected. Merge SHA: `9d9dae8574c9bcddebd58079ef345a3f35074209`.
