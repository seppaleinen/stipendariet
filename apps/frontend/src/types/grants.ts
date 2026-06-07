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

export interface Application {
  id: string;
  grantId: string;
  grantTitle: string;
  status: "draft" | "submitted" | "approved" | "rejected";
  createdAt?: string;
  updatedAt?: string;
  content?: string;
  notes?: string;
}

// Life situation options
export type LifeSituation =
  | "low_income"
  | "single_parent"
  | "widow"
  | "pensioner"
  | "student"
  | "youth"
  | "unemployed";

// Health condition options
export type HealthCondition =
  | "mobility"
  | "vision_hearing"
  | "mental_health"
  | "allergy"
  | "diabetes"
  | "cancer"
  | "chronic_illness";

// Occupation/background options
export type Occupation =
  | "hotel_restaurant"
  | "retail"
  | "maritime"
  | "crafts"
  | "healthcare"
  | "agriculture"
  | "arts"
  | "journalism";

// Support purpose options
export type SupportPurpose =
  | "education"
  | "financial_aid"
  | "health_care"
  | "projects"
  | "research"
  | "travel"
  | "equipment";

// Structured profile for matching
export interface Profile {
  // Section 1: Geography
  countyCode?: string;
  municipalityCode?: string;

  // Section 2: Life Situation
  lifeSituations?: LifeSituation[];

  // Section 3: Health & Disability
  healthConditions?: HealthCondition[];
  healthDetails?: string;

  // Section 4: Occupation & Background
  occupations?: Occupation[];

  // Section 5: Support Purpose
  supportPurposes?: SupportPurpose[];

  // Legacy data from old profile format
  legacyData?: Record<string, unknown>;
}

// Alias for backward compatibility
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

// Extended family setup types
export interface FamilySetup {
  id?: string;
  family: {
    municipality: string;
    adults: number;
    children: number;
    maritalStatus: "married" | "cohabiting" | "single" | "other";
    email?: string;
    phone?: string;
  };
  children: {
    age: number;
    diagnoses: (
      | "adhd"
      | "autism"
      | "intellectual_disability"
      | "cp"
      | "acquired_brain_injury"
      | "other"
    )[];
    otherDiagnosis?: string;
    needLevel: "0" | "1" | "2" | "3";
    mobility: {
      wheelchair?: boolean;
      assistiveDevices?: string;
      stairs?: boolean;
      supervision?: boolean;
    };
  }[];
  economy: {
    financialDifficulties?: boolean;
    monthlyIncome?: string;
    employment?:
    | "full_time"
    | "part_time"
    | "sick_leave"
    | "unemployed"
    | "other";
    benefits: {
      unemployment?: boolean;
      sickness?: boolean;
      allowance?: boolean;
      none?: boolean;
    };
  };
  personalDescription?: string;
  contactInformation?: Record<string, unknown>;
  livingSituation?: string;
  additionalNotes?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface GeneratedApplication {
  content: string;
  grantId: string;
}
