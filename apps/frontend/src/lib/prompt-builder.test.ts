import { describe, it, expect } from "vitest";
import { buildApplicationPrompt, labelsFor, truncateDescription } from "./prompt-builder";
import type { Grant, Profile } from "@/types/grants";
import {
  LIFE_SITUATION_OPTIONS,
  SUPPORT_PURPOSE_OPTIONS,
} from "./profile-options";

const grant: Grant = {
  id: "foundation-1",
  title: "Stiftelsen Test",
  summary: "En teststiftelse",
  description: "Beskrivning av stiftelsen",
  provider: "Testutgivare",
  category: "test",
  tags: [],
  isRecurring: false,
  purpose: "Att stödja utbildning",
};

const fullProfile: Profile = {
  name: "Min profil",
  countyCode: "01",
  municipalityCode: "0180", // Stockholm
  lifeSituations: ["student", "low_income"],
  healthConditions: ["mobility"],
  healthDetails: "Använder rullstol",
  occupations: ["arts"],
  supportPurposes: ["education", "equipment"],
};

describe("labelsFor", () => {
  it("maps enum values to Swedish labels", () => {
    expect(labelsFor(LIFE_SITUATION_OPTIONS, ["student", "low_income"])).toEqual([
      "Student",
      "Låg inkomst",
    ]);
  });

  it("passes through unknown values unchanged", () => {
    expect(labelsFor(LIFE_SITUATION_OPTIONS, ["mystery_value"])).toEqual([
      "mystery_value",
    ]);
  });

  it("returns empty array for missing values", () => {
    expect(labelsFor(SUPPORT_PURPOSE_OPTIONS, undefined)).toEqual([]);
    expect(labelsFor(SUPPORT_PURPOSE_OPTIONS, null)).toEqual([]);
    expect(labelsFor(SUPPORT_PURPOSE_OPTIONS, [])).toEqual([]);
  });
});

describe("buildApplicationPrompt", () => {
  it("includes municipality and county names resolved from codes", () => {
    const prompt = buildApplicationPrompt(fullProfile, grant);
    expect(prompt).toContain("Kommun: Stockholm");
    expect(prompt).toContain("Län: Stockholms län");
  });

  it("translates structured profile fields into Swedish labels", () => {
    const prompt = buildApplicationPrompt(fullProfile, grant);
    expect(prompt).toContain("Livssituation: Student, Låg inkomst");
    expect(prompt).toContain("Hälsa: Rörelsehinder");
    expect(prompt).toContain("Hälsodetaljer: Använder rullstol");
    expect(prompt).toContain("Yrkesbakgrund: Konst & kultur");
    expect(prompt).toContain("Utbildning, Utrustning");
  });

  it("includes foundation context", () => {
    const prompt = buildApplicationPrompt(fullProfile, grant);
    expect(prompt).toContain("Namn: Stiftelsen Test");
    expect(prompt).toContain("Ändamål: Att stödja utbildning");
    expect(prompt).toContain("Utgivare: Testutgivare");
  });

  it("handles an empty profile without crashing and marks fields as missing", () => {
    const prompt = buildApplicationPrompt({}, grant);
    expect(prompt).toContain("Inga angivna");
    expect(prompt).not.toContain("undefined");
    expect(prompt).not.toContain("[object Object]");
  });

  it("works without a foundation selected", () => {
    const prompt = buildApplicationPrompt(fullProfile, null);
    expect(prompt).not.toContain("Stiftelse/Stipendium som söks");
    expect(prompt).toContain("Livssituation: Student, Låg inkomst");
  });
});

describe("buildApplicationPrompt — self-description opt-in", () => {
  const swedishDescription =
    "Jag är en 25-årig student i Uppsala som studerar till lärare. " +
    "Jag har nedsatt hörsel och använder hörapparat. Eftersom jag har en " +
    "delad föräldrakapacitet och låg inkomst söker jag stöd för att kunna " +
    " fortsätta min utbildning och skaffa nödvändiga studiehjälpmedel.";

  it("default (opt-in omitted) excludes the description section", () => {
    const prompt = buildApplicationPrompt(fullProfile, grant);
    expect(prompt).not.toContain("Självbeskrivning");
    expect(prompt).not.toContain(
      "Sökändens egen beskrivning kan vara på vilket språk",
    );
    expect(prompt).toContain("Livssituation: Student, Låg inkomst");
  });

  it("opt-in includes verbatim description, header, and OBS instruction (D3 additive)", () => {
    const profile = { ...fullProfile, selfDescription: swedishDescription };
    const prompt = buildApplicationPrompt(profile, grant, {
      useSelfDescription: true,
    });
    expect(prompt).toContain("Självbeskrivning (sökändens egna ord):");
    expect(prompt).toContain(swedishDescription);
    expect(prompt).toContain(
      "OBS: Sökändens egen beskrivning kan vara på vilket språk som helst — ansökan skrivs ändå på svenska.",
    );
    // Structured selections preserved (D3 additive)
    expect(prompt).toContain("Livssituation: Student, Låg inkomst");
    // Foundation context still present
    expect(prompt).toContain("Namn: Stiftelsen Test");
  });

  it("truncates descriptions longer than 2000 chars", () => {
    const profile = { ...fullProfile, selfDescription: "x".repeat(2050) };
    const prompt = buildApplicationPrompt(profile, grant, {
      useSelfDescription: true,
    });
    expect(prompt).toContain("x".repeat(2000) + "…");
    expect(prompt).not.toContain("x".repeat(2001));
    expect(prompt).toContain("Självbeskrivning (sökändens egna ord):");
    expect(prompt).toContain(
      "OBS: Sökändens egen beskrivning kan vara på vilket språk som helst — ansökan skrivs ändå på svenska.",
    );
  });

  it("omits the section entirely for empty/whitespace/null/undefined descriptions", () => {
    for (const value of ["", "   ", null, undefined]) {
      const profile = { ...fullProfile, selfDescription: value };
      const prompt = buildApplicationPrompt(profile, grant, {
        useSelfDescription: true,
      });
      expect(prompt).not.toContain("Självbeskrivning");
      expect(prompt).not.toContain(
        "OBS: Sökändens egen beskrivning kan vara på vilket språk",
      );
      // Structured content intact
      expect(prompt).toContain("Livssituation: Student, Låg inkomst");
    }
  });

  it("places the self-description section after structured lines and before the foundation block", () => {
    const profile = { ...fullProfile, selfDescription: swedishDescription };
    const prompt = buildApplicationPrompt(profile, grant, {
      useSelfDescription: true,
    });
    const selfDescIndex = prompt.indexOf("Självbeskrivning");
    const foundationIndex = prompt.indexOf("Stiftelse/Stipendium som söks");
    expect(selfDescIndex).toBeGreaterThan(-1);
    expect(foundationIndex).toBeGreaterThan(-1);
    expect(selfDescIndex).toBeLessThan(foundationIndex);
  });

  it("foundation context is unaffected in both modes", () => {
    const profile = { ...fullProfile, selfDescription: swedishDescription };
    const withOptIn = buildApplicationPrompt(profile, grant, {
      useSelfDescription: true,
    });
    const withoutOptIn = buildApplicationPrompt(profile, grant);
    for (const line of [
      "Namn: Stiftelsen Test",
      "Beskrivning: Beskrivning av stiftelsen",
      "Sammanfattning: En teststiftelse",
      "Ändamål: Att stödja utbildning",
      "Utgivare: Testutgivare",
    ]) {
      expect(withOptIn).toContain(line);
      expect(withoutOptIn).toContain(line);
    }
  });
});

describe("truncateDescription", () => {
  it("returns empty string for null, undefined, and whitespace-only input", () => {
    expect(truncateDescription(null)).toBe("");
    expect(truncateDescription(undefined)).toBe("");
    expect(truncateDescription("")).toBe("");
    expect(truncateDescription("   ")).toBe("");
    expect(truncateDescription("\t\n  ")).toBe("");
  });

  it("returns verbatim (no ellipsis) for exactly 2000 chars", () => {
    const input = "x".repeat(2000);
    const result = truncateDescription(input);
    expect(result).toBe("x".repeat(2000));
    expect(result).not.toContain("…");
    expect(result.length).toBe(2000);
  });

  it("trims leading/trailing whitespace before measuring", () => {
    const input = "  " + "x".repeat(2000) + "  ";
    const result = truncateDescription(input);
    expect(result).toBe("x".repeat(2000));
    expect(result.length).toBe(2000);
  });

  it("returns 2000 chars + ellipsis for 2001+ chars (total length 2001)", () => {
    const input = "x".repeat(2001);
    const result = truncateDescription(input);
    expect(result).toBe("x".repeat(2000) + "…");
    expect(result.length).toBe(2001);
  });

  it("uses a single U+2026 ellipsis character", () => {
    const input = "x".repeat(2050);
    const result = truncateDescription(input);
    expect(result).toContain("…");
    expect(result.split("…").length - 1).toBe(1);
  });
});
