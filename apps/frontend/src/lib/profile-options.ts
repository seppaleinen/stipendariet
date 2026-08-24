/**
 * Shared Swedish label definitions for structured profile fields.
 *
 * Used by ProfileSetup (form rendering) and the Generate page
 * (AI prompt building) so enum values are translated to human-readable
 * Swedish in exactly one place.
 */

export interface ProfileFieldOption {
  value: string;
  label: string;
  description: string;
}

export const LIFE_SITUATION_OPTIONS: ProfileFieldOption[] = [
  { value: "low_income", label: "Låg inkomst", description: "Ekonomiska svårigheter" },
  { value: "single_parent", label: "Ensamstående förälder", description: "Ensam vårdnadshavare" },
  { value: "widow", label: "Änka/änkling", description: "Förlorat make/maka" },
  { value: "pensioner", label: "Pensionär", description: "65+ eller förtidspensionär" },
  { value: "student", label: "Student", description: "Studerande på högskola/universitet" },
  { value: "youth", label: "Ung (under 30)", description: "Ung vuxen" },
  { value: "unemployed", label: "Arbetslös", description: "Arbetssökande" },
];

export const HEALTH_CONDITION_OPTIONS: ProfileFieldOption[] = [
  { value: "mobility", label: "Rörelsehinder", description: "Nedsatt rörelseförmåga" },
  { value: "vision_hearing", label: "Syn-/hörselnedsättning", description: "Nedsatt syn eller hörsel" },
  { value: "mental_health", label: "Psykisk ohälsa", description: "Depression, ångest, etc." },
  { value: "allergy", label: "Allergi", description: "Allergier eller överkänslighet" },
  { value: "diabetes", label: "Diabetes", description: "Typ 1 eller 2 diabetes" },
  { value: "cancer", label: "Cancer", description: "Cancersjukdom" },
  { value: "chronic_illness", label: "Kronisk sjukdom", description: "Annan kronisk sjukdom" },
];

export const OCCUPATION_OPTIONS: ProfileFieldOption[] = [
  { value: "hotel_restaurant", label: "Hotell & restaurang", description: "Hotell- och restaurangbranschen" },
  { value: "retail", label: "Detaljhandel", description: "Butik och försäljning" },
  { value: "maritime", label: "Sjöfart/fiske", description: "Sjöfart och fiskerinäring" },
  { value: "crafts", label: "Hantverk", description: "Hantverksyrken" },
  { value: "healthcare", label: "Vård & omsorg", description: "Sjukvård och omsorg" },
  { value: "agriculture", label: "Jordbruk/skogsbruk", description: "Lantbruk och skog" },
  { value: "arts", label: "Konst & kultur", description: "Konstnärlig verksamhet" },
  { value: "journalism", label: "Journalistik", description: "Media och skrivande" },
];

export const SUPPORT_PURPOSE_OPTIONS: ProfileFieldOption[] = [
  { value: "education", label: "Utbildning", description: "Studier och fortbildning" },
  { value: "financial_aid", label: "Ekonomiskt stöd", description: "Bidrag till livsomkostnader" },
  { value: "health_care", label: "Vård & behandling", description: "Medicinsk vård eller rehabilitering" },
  { value: "projects", label: "Projekt", description: "Verksamhet eller evenemang" },
  { value: "research", label: "Forskning", description: "Vetenskapligt arbete" },
  { value: "travel", label: "Resor", description: "Semester eller resor" },
  { value: "equipment", label: "Utrustning", description: "Hjälpmedel eller utrustning" },
];
