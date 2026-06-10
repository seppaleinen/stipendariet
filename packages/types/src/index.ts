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
}

// ── API Response Wrappers ──────────────────────────────────────────────

export interface GrantsResponse {
  grants: Grant[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

export interface MatchedFoundation {
  foundation: {
    id: number;
    foundation_id: number;
    name: string;
    summary: string | null;
    translated_purpose: string | null;
    category: string | null;
  };
  similarity_score: number;
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
