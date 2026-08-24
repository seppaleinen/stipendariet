import { describe, it, expect } from "vitest";
import { buildApplicationPrompt, labelsFor } from "./prompt-builder";
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
