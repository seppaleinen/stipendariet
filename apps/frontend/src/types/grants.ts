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
