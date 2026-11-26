## Unreleased
### Changed
- Backend env: migrate `SEARXNG_URL` from a kustomize postRenderer patch to chart `envFrom` Secret (stipendariet chart 0.15.15). The chart now emits the exact underscore-preserved `SEARXNG_URL` name the backend reads (`backend/app/core/config.py`); the fleet-infra postRenderer hack is removed. `LITELLM_API_KEY` continues to be delivered via Sops-encrypted `secretKeyRef` postRenderer patches.

### Fixed
- Issue #38: `SEARXNG_URL` was emitted as `SEARXNG-URL` (hyphen) by the chart's env-name transform (`upper | replace "_" "-"`), so the backend never saw the var. Delivery now goes through the chart's `envFrom` Secret, which preserves the underscore name the app expects.
