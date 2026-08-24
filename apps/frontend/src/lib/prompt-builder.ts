import type { Grant, Profile } from "@/types/grants";
import {
  LIFE_SITUATION_OPTIONS,
  HEALTH_CONDITION_OPTIONS,
  OCCUPATION_OPTIONS,
  SUPPORT_PURPOSE_OPTIONS,
} from "@/lib/profile-options";
import { findCountyByCode, findMunicipalityByCode } from "@/data/swedish-regions";

/**
 * Maps stored profile enum values to their Swedish labels.
 * Unknown values pass through unchanged so no data is silently dropped.
 */
export function labelsFor(
  options: { value: string; label: string }[],
  values: string[] | undefined | null,
): string[] {
  if (!values || values.length === 0) return [];
  const byValue = new Map(options.map((o) => [o.value, o.label]));
  return values.map((v) => byValue.get(v) ?? v);
}

function joinLabels(labels: string[]): string {
  return labels.length > 0 ? labels.join(", ") : "Inga angivna";
}

/**
 * Builds the Swedish AI prompt for a grant application from the user's
 * structured profile and the selected grant/foundation.
 */
export function buildApplicationPrompt(
  profile: Profile,
  foundation: Grant | null,
): string {
  let prompt =
    "Skriv en personlig och övertygande ansökan på svenska baserat på följande information:\n\n";

  // Applicant geography
  if (profile.countyCode || profile.municipalityCode) {
    const county = profile.countyCode
      ? findCountyByCode(profile.countyCode)?.name
      : undefined;
    const municipality =
      profile.countyCode && profile.municipalityCode
        ? findMunicipalityByCode(profile.countyCode, profile.municipalityCode)?.name
        : undefined;
    prompt += "Var du bor:\n";
    if (municipality) prompt += `- Kommun: ${municipality}\n`;
    if (county) prompt += `- Län: ${county}\n`;
    prompt += "\n";
  }

  // Structured profile sections
  prompt += "Profil:\n";
  prompt += `- Livssituation: ${joinLabels(labelsFor(LIFE_SITUATION_OPTIONS, profile.lifeSituations))}\n`;
  prompt += `- Hälsa: ${joinLabels(labelsFor(HEALTH_CONDITION_OPTIONS, profile.healthConditions))}\n`;
  if (profile.healthDetails) {
    prompt += `- Hälsodetaljer: ${profile.healthDetails}\n`;
  }
  prompt += `- Yrkesbakgrund: ${joinLabels(labelsFor(OCCUPATION_OPTIONS, profile.occupations))}\n`;
  prompt += `Sökända syften med stödet: ${joinLabels(labelsFor(SUPPORT_PURPOSE_OPTIONS, profile.supportPurposes))}\n`;

  // Foundation context
  if (foundation) {
    prompt += `\nStiftelse/Stipendium som söks:\n`;
    prompt += `- Namn: ${foundation.title}\n`;
    prompt += `- Beskrivning: ${foundation.description || "Ej angiven"}\n`;
    if (foundation.summary) {
      prompt += `- Sammanfattning: ${foundation.summary}\n`;
    }
    if (foundation.purpose) {
      prompt += `- Ändamål: ${foundation.purpose}\n`;
    }
    if (foundation.provider) {
      prompt += `- Utgivare: ${foundation.provider}\n`;
    }
  }

  // Style and structure instructions (preserved from the legacy prompt)
  prompt +=
    "\nINSTRUKTION:\nDu ska agera som en erfaren, svensk bidragsansökan-skrivare med expertis inom finansiering från stiftelser och fonder. Skriv ett personligt, övertygande och professionellt följebrev/ansökan till den specifika stiftelsen med följande stil och struktur:\n\n";
  prompt += "STIL OCH TON:\n";
  prompt +=
    "1. Naturlig svenska: Texten får INTE låta som en översättning från engelska. Undvik uttryck som 'jag hoppas detta brev finner dig väl' eller överdrivna adjektiv.\n";
  prompt +=
    "2. Balans: Var ödmjuk men kompetent. I Sverige uppskattas saklighet. Skryt inte, utan beskriv konkret vilken nytta projektet gör.\n";
  prompt +=
    "3. Artighet: Använd en formell men varm ton. Undvik byråkratiskt 'kanslisvenska'.\n";
  prompt +=
    "4. Struktur: Ämnesraden ska vara tydlig. Inledningen ska fånga intresset direkt.\n\n";
  prompt += "STRUKTUR PÅ MAILET:\n";
  prompt += "- Ämnesrad: Kort, tydlig och relevant för ansökan.\n";
  prompt += "- Hälsningsfras: Formell men inte stel.\n";
  prompt +=
    "- 'Hook': Varför söker jag just DENNA stiftelse? Koppla mitt syfte till deras ändamål.\n";
  prompt +=
    "- Projektet: Vad ska göras? Vem hjälps? Varför behövs pengarna?\n";
  prompt +=
    "- Avslut: Tydlig information om bifogade dokument och en artig, hoppfull hälsning.\n\n";
  prompt +=
    "Ersätt alla platshållare som [Your Name], [Your Contact Information] och Dear [Recipient's Name] med faktiska namn och kontaktuppgifter. Skriv på svenska.";

  return prompt;
}
