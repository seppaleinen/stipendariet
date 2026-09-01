// ── Shared types for @stipendariet/types ──────────────────────────────
// These types are shared across apps/frontend and apps/admin.
// Import via `import { User, Profile, ... } from '@stipendariet/types'`

// ── Auth ──────────────────────────────────────────────────────────────

/** Unified user type matching backend's /auth/me response */
export interface User {
  id: string;
  email: string;
  name?: string;
  role?: string;
  avatar?: string;
}

// ── Matching Profile ───────────────────────────────────────────────────

export type LifeSituation =
  | "low_income"
  | "single_parent"
  | "widow"
  | "pensioner"
  | "student"
  | "youth"
  | "unemployed";

export type HealthCondition =
  | "mobility"
  | "vision_hearing"
  | "mental_health"
  | "allergy"
  | "diabetes"
  | "cancer"
  | "chronic_illness";

export type Occupation =
  | "hotel_restaurant"
  | "retail"
  | "maritime"
  | "crafts"
  | "healthcare"
  | "agriculture"
  | "arts"
  | "journalism";

export type SupportPurpose =
  | "education"
  | "financial_aid"
  | "health_care"
  | "projects"
  | "research"
  | "travel"
  | "equipment";

/** Structured matching profile for grant recommendations */
export interface Profile {
  id?: number;
  name?: string;
  isDefault?: boolean;
  countyCode?: string;
  municipalityCode?: string;
  lifeSituations?: LifeSituation[];
  healthConditions?: HealthCondition[];
  healthDetails?: string;
  occupations?: Occupation[];
  supportPurposes?: SupportPurpose[];
  /** Self-description: the user's situation in their own words (alternative matching text source) */
  selfDescription?: string | null;
  legacyData?: Record<string, unknown>;
}

// ── Application ────────────────────────────────────────────────────────

export type ApplicationStatus = "draft" | "submitted" | "approved" | "rejected";

export interface Application {
  id: string;
  grantId: string;
  grantTitle: string;
  status: ApplicationStatus;
  createdAt?: string;
  updatedAt?: string;
  content?: string;
  notes?: string;
}

// ── Grant / Foundation (domain) ────────────────────────────────────────

export interface Grant {
  id: string;
  title: string;
  summary: string;
  description: string;
  provider: string;
  amount?: string;
  deadline?: string;
  category: string;
  tags: string[];
  isRecurring: boolean;
  websiteUrl?: string;
  isFavorite?: boolean;
  isSaved?: boolean;
  // Foundation-specific fields
  orgnr?: string;
  purpose?: string;
  translatedPurpose?: string;
  address?: string;
  postnr?: string;
  postort?: string;
  coAddress?: string;
  phone?: string;
  signature?: string;
  roles?: { type?: string; name?: string; number?: string; address?: string; phone?: string; main_responsible?: string }[];
  // Enrichment fields (mapped from backend snake_case)
  applicationDeadline?: string;
  applicationStart?: string;
  applicationMethod?: string;
  contactEmail?: string;
  contactPhone?: string;
  whoCanApply?: string;
  enrichedDescription?: string;
}

// ── API Response Wrappers ──────────────────────────────────────────────

export interface GrantsResponse {
  grants: Grant[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

/** LLM-extracted eligibility footprint (Service area) of a Foundation,
 *  derived from its name and purpose text. Stored as JSON on the backend
 *  and mapped to camelCase on the frontend. */
export interface ParsedServiceArea {
  municipality_code: string;
  county_code: string;
  municipality_name: string;
  county_name: string;
  source_text: string;
  confidence: string;
  /** Street / neighborhood level detail when the Service area is finer than a municipality */
  service_area_detail?: string;
}

export interface MatchedFoundation {
  foundation: {
    id: number;
    foundation_id: number;
    name: string;
    summary: string | null;
    translated_purpose: string | null;
    category: string | null;
    parsedServiceArea?: ParsedServiceArea;
  };
  similarity_score: number;
}

// ── Translation judging (admin) ────────────────────────────────────────

/** A foundation row for the admin translation-judging page: original purpose
 *  + translated purpose side by side, with parsed service-area metadata. */
export interface FoundationTranslationListItem {
  id: number;
  foundation_id: number;
  name: string;
  orgnr: string | null;
  purpose: string | null;
  translated_purpose: string | null;
  summary: string | null;
  address: string | null;
  postnr: string | null;
  postort: string | null;
  county_code: string | null;
  municipality_code: string | null;
  parsed_service_area: ParsedServiceArea | null;
  category: string | null;
  last_updated: string | null;
}

/** Paginated response for the admin foundation-translation list endpoint. */
export interface PaginatedFoundationsTranslationResponse {
  total: number;
  page: number;
  page_size: number;
  items: FoundationTranslationListItem[];
}

// ── Swedish Geography ──────────────────────────────────────────────────

export interface Municipality {
  code: string;
  name: string;
}

export interface County {
  code: string;
  name: string;
  municipalities: Municipality[];
}
