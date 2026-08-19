// Re-export shared types from @stipendariet/types as single source of truth
export type {
  Grant,
  Application,
  ApplicationStatus,
  LifeSituation,
  HealthCondition,
  Occupation,
  SupportPurpose,
  Profile,
  User,
} from '@stipendariet/types';

// ── App-specific types (not yet extracted to shared package) ───────────

export type FamilyProfile = Profile;

export interface ChildNeed {
  childId?: string;
  diagnoses?:
  | "adhd"[]
  | "autism"[]
  | "cp"[]
  | "mobility_impairment"[]
  | "other"[]
  | string[];
  needDegree?: number;
  otherDiagnosis?: string | null;
}

export interface ContactInfo {
  email?: string;
  phone?: string;
  address?: string;
  [key: string]: string | number | boolean | undefined | null;
}

export interface FamilyMember {
  name: string;
  age: number;
  role: "adult" | "child" | string;
  occupation?: string;
  income?: string;
  education?: string;
  healthStatus?: string;
  additionalInfo?: string;
  contactInfo?: ContactInfo;
}

export interface GeneratedApplication {
  content: string;
  grantId: string;
}
