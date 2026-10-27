// ── Admin-specific types for @stipendariet/types ───────────────────────
// These types are used by the admin panel and represent data contracts
// with the backend. UI-only state types remain in the admin app.

// ── Scholarship (admin queue/review) ────────────────────────────────────

/**
 * **ORPHANED FEATURE — NOT A LIVE API CONTRACT**
 *
 * The `scholarships` table was dropped in alembic migration
 * `b64ec2432846_add_multi_profile_support.py` (line 43: `op.drop_table('scholarships')`).
 * No `/scholarships/*` routes exist in `backend/app/api/v1/routers/`.
 *
 * The admin UI (`QueuePage`, `ReviewPage`) still calls `/scholarships/queue`,
 * `/scholarships/${id}/review`, etc. — these will 404 at runtime.
 *
 * These types are kept here so the admin UI compiles cleanly while the
 * orphaned feature is tracked separately. Do NOT treat this as a live
 * backend contract.
 */
export interface Scholarship {
  id: string;
  name: string;
  organization_name: string;
  description: string | null;
  requirements: string | null;
  amount: string | null;
  deadline: string | null;
  application_method: string | null;
  official_url: string | null;
  status: 'NEW' | 'NEEDS_REVIEW' | 'PUBLISHED' | 'FAILED';
  raw_scraped_content: string | null;
  embedding: string | null;
  created_at: string;
  updated_at: string | null;
}

/**
 * **ORPHANED FEATURE — NOT A LIVE API CONTRACT**
 *
 * See the `Scholarship` type for the full orphaned-feature note.
 * The `/scholarships/queue` endpoint does not currently exist.
 */
export interface ScholarshipQueueItem {
  id: string;
  name: string;
  organization_name: string;
  status: 'NEW' | 'FAILED';
  created_at: string;
}

// ── Enrichment Jobs (admin dashboard) ───────────────────────────────────

/**
 * Aggregated foundation enrichment statistics returned by the admin
 * enrichment status endpoint. This is a stats aggregate — NOT the same
 * as the backend `EnrichmentStatus` enum in
 * `app/services/enrichment_schemas.py` (UNPROCESSED/PENDING/COMPLETED/FAILED).
 */
export type FoundationStats = {
  total_foundations: number;
  translated: number;
  untranslated: number;
  embedded: number;
  not_embedded: number;
  translation_percentage: number;
  embedding_percentage: number;
};

/**
 * Enrichment progress summary returned by the admin enrichment status
 * endpoint. Contains aggregate counts and completion percentage.
 */
export type EnrichmentStats = {
  total: number;
  counts: Record<string, number>;
  completed_percentage: number;
  failed_count: number;
  remaining: number;
};

/**
 * Active Celery task reference. Null when no enrichment job is running.
 * Matches the shape returned by the admin active-jobs endpoint.
 */
export type ActiveJob = {
  task_id: string;
  status: string;
} | null;

/**
 * Map of job names to their currently active task (or null).
 * Returned by the admin active-jobs summary endpoint.
 */
export type ActiveJobsSummary = Record<string, ActiveJob>;

/**
 * Foundation search result item. Returned by the admin foundation
 * search endpoint when looking up foundations by name or orgnr.
 */
export type FoundationSearchResult = {
  id: number;
  name: string;
  orgnr: string | null;
};

/**
 * Default prompts and model configuration for enrichment jobs.
 * Returned by the admin enrichment defaults endpoint.
 */
export type EnrichmentDefaults = {
  validation_system_prompt: string;
  validation_user_prompt: string;
  extraction_system_prompt: string;
  extraction_user_prompt: string;
  model: string;
};