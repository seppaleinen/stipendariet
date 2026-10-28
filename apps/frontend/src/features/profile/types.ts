import * as z from "zod";
import type { Profile } from "@/lib/api";

/**
 * Zod schema for the structured profile setup form.
 *
 * Single source of truth: the form component and the shared type both
 * derive from this schema, so the runtime validation and the TypeScript
 * shape can never drift apart.
 */
export const profileSetupSchema = z.object({
  name: z.string().min(1, "Namn krävs"),
  // Section 1: Geography
  countyCode: z.string().optional(),
  municipalityCode: z.string().optional(),

  // Section 2: Life Situation
  lifeSituations: z.array(z.string()).optional(),

  // Section 3: Health
  healthConditions: z.array(z.string()).optional(),
  healthDetails: z.string().optional(),

  // Section 4: Occupations
  occupations: z.array(z.string()).optional(),

  // Section 5: Support Purpose
  supportPurposes: z.array(z.string()).optional(),

  // Self-description: the user's situation in their own words
  selfDescription: z.string().max(2000, "Max 2000 tecken").optional(),
});

/** Form values shape inferred from the zod schema above. */
export type ProfileSetupFormValues = z.infer<typeof profileSetupSchema>;

/**
 * Interface describing the profile CRUD function signatures exposed by
 * `@/lib/api`. The service wrapper in `./services/profileService` is a
 * plain re-export of these functions; this interface exists so callers
 * (e.g. ProfileContext) can depend on the feature module's surface
 * without reaching into `@/lib/api` directly.
 */
export interface ProfileService {
  listProfiles(): Promise<Profile[]>;
  getProfileById(id: number): Promise<Profile>;
  createProfile(profile: Profile): Promise<Profile>;
  updateProfileById(id: number, profile: Profile): Promise<Profile>;
  deleteProfile(id: number): Promise<void>;
}