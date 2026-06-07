import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  mapGrantFromBackend,
  mapApplicationFromBackend,
  mapBackendProfileToFrontend,
  mapFrontendProfileToBackend,
} from "@/lib/api";

describe("mapGrantFromBackend", () => {
  it("maps basic grant fields", () => {
    const backend: Record<string, unknown> = {
      id: "123",
      name: "Test Grant",
      description: "Test description",
      organization: "Test Org",
      amount: "10000 SEK",
      deadline: "2025-12-31",
      category: "Education",
      tags: ["student", "scholarship"],
      cadence: "årlig",
      link: "https://example.com",
    };

    const grant = mapGrantFromBackend(backend);

    expect(grant.id).toBe("123");
    expect(grant.title).toBe("Test Grant");
    expect(grant.description).toBe("Test description");
    expect(grant.provider).toBe("Test Org");
    expect(grant.amount).toBe("10000 SEK");
    expect(grant.deadline).toBeDefined();
    expect(grant.category).toBe("Education");
    expect(grant.tags).toEqual(["student", "scholarship"]);
    expect(grant.isRecurring).toBe(true);
    expect(grant.websiteUrl).toBe("https://example.com");
  });

  it("uses application_deadline as fallback for deadline", () => {
    const backend: Record<string, unknown> = {
      id: "123",
      name: "Test",
      application_deadline: "2025-06-30",
    };

    const grant = mapGrantFromBackend(backend);
    expect(grant.deadline).toBeDefined();
  });

  it("uses title when name is missing", () => {
    const backend: Record<string, unknown> = {
      id: "123",
      title: "Title Grant",
    };

    const grant = mapGrantFromBackend(backend);
    expect(grant.title).toBe("Title Grant");
  });

  it("uses description when summary is missing", () => {
    const backend: Record<string, unknown> = {
      id: "123",
      name: "Test",
      description: "Desc only",
    };

    const grant = mapGrantFromBackend(backend);
    expect(grant.summary).toBe("Desc only");
  });

  it("provides fallback values for missing fields", () => {
    const backend: Record<string, unknown> = {
      id: "123",
    };

    const grant = mapGrantFromBackend(backend);
    expect(grant.title).toBe("Namn saknas");
    expect(grant.provider).toBe("Okänd utgivare");
    expect(grant.summary).toBe("Ingen sammanfattning tillgänglig");
    expect(grant.description).toBe("Ingen beskrivning tillgänglig");
    expect(grant.category).toBe("Diverse");
    expect(grant.tags).toEqual([]);
    expect(grant.isRecurring).toBe(false);
    expect(grant.amount).toBeUndefined();
  });

  it("maps foundation-specific fields", () => {
    const backend: Record<string, unknown> = {
      id: "123",
      name: "Test",
      orgnr: "123456-7890",
      purpose: "Study support",
      translated_purpose: "Stöd för studier",
      address: "Storgatan 1",
      postnr: "12345",
      postort: "Stockholm",
      co_address: "c/o Other",
      phone: "08-123456",
      signature: "John Doe",
      roles: ["student", "parent"],
    };

    const grant = mapGrantFromBackend(backend);

    expect(grant.orgnr).toBe("123456-7890");
    expect(grant.purpose).toBe("Study support");
    expect(grant.translatedPurpose).toBe("Stöd för studier");
    expect(grant.address).toBe("Storgatan 1");
    expect(grant.postnr).toBe("12345");
    expect(grant.postort).toBe("Stockholm");
    expect(grant.coAddress).toBe("c/o Other");
    expect(grant.phone).toBe("08-123456");
    expect(grant.signature).toBe("John Doe");
    expect(grant.roles).toEqual(["student", "parent"]);
  });

  it("handles numeric id", () => {
    const backend: Record<string, unknown> = {
      id: 456,
      name: "Numeric ID Grant",
    };

    const grant = mapGrantFromBackend(backend);
    expect(grant.id).toBe("456");
  });

  it("handles non-recurring grant (no cadence or cadence without 'år')", () => {
    const backend: Record<string, unknown> = {
      id: "123",
      name: "Test",
      cadence: "monthly",
    };

    const grant = mapGrantFromBackend(backend);
    expect(grant.isRecurring).toBe(false);
  });
});

describe("mapApplicationFromBackend", () => {
  it("maps application fields correctly", () => {
    const backend: Record<string, unknown> = {
      id: "app-123",
      grant_id: "grant-456",
      grant_name: "Test Grant",
      status: "approved",
      created_at: "2025-01-01",
      updated_at: "2025-06-01",
      content: "Application content here",
    };

    const app = mapApplicationFromBackend(backend);

    expect(app.id).toBe("app-123");
    expect(app.grantId).toBe("grant-456");
    expect(app.grantTitle).toBe("Test Grant");
    expect(app.status).toBe("approved");
    expect(app.content).toBe("Application content here");
    expect(app.createdAt).toBe("2025-01-01");
    expect(app.updatedAt).toBe("2025-06-01");
  });

  it("handles grant_id as number", () => {
    const backend: Record<string, unknown> = {
      id: "app-123",
      grant_id: 789,
      status: "submitted",
    };

    const app = mapApplicationFromBackend(backend);
    expect(app.grantId).toBe("789");
  });

  it("handles grantId camelCase as fallback", () => {
    const backend: Record<string, unknown> = {
      id: "app-123",
      grantId: "camel-case-grant",
      status: "draft",
    };

    const app = mapApplicationFromBackend(backend);
    expect(app.grantId).toBe("camel-case-grant");
  });

  it("handles unknown status as draft", () => {
    const backend: Record<string, unknown> = {
      id: "app-123",
      status: "pending_review",
    };

    const app = mapApplicationFromBackend(backend);
    expect(app.status).toBe("draft");
  });

  it("handles application without optional fields", () => {
    const backend: Record<string, unknown> = {
      id: "app-123",
      status: "submitted",
    };

    const app = mapApplicationFromBackend(backend);
    expect(app.grantTitle).toBe("");
    expect(app.content).toBeUndefined();
    expect(app.createdAt).toBeUndefined();
    expect(app.updatedAt).toBeUndefined();
  });
});

describe("mapBackendProfileToFrontend", () => {
  it("maps profile fields with snake_case", () => {
    const backend = {
      id: 1,
      name: "Test Profile",
      is_default: true,
      county_code: "AB001",
      municipality_code: "AB001",
      life_situations: ["student"],
      health_conditions: ["asthma"],
      health_details: "Mild asthma",
      occupations: ["student"],
      support_purposes: ["education"],
      legacy_data: { source: "legacy" },
    };

    const profile = mapBackendProfileToFrontend(backend);

    expect(profile.id).toBe(1);
    expect(profile.name).toBe("Test Profile");
    expect(profile.isDefault).toBe(true);
    expect(profile.countyCode).toBe("AB001");
    expect(profile.municipalityCode).toBe("AB001");
    expect(profile.lifeSituations).toEqual(["student"]);
    expect(profile.healthConditions).toEqual(["asthma"]);
    expect(profile.healthDetails).toBe("Mild asthma");
    expect(profile.occupations).toEqual(["student"]);
    expect(profile.supportPurposes).toEqual(["education"]);
    expect(profile.legacyData).toEqual({ source: "legacy" });
  });

  it("maps profile fields with camelCase", () => {
    const backend = {
      id: 2,
      name: "Camel Profile",
      is_default: false,
      countyCode: "AB002",
      municipalityCode: "AB002",
      lifeSituations: ["employed"],
      healthConditions: ["none"],
      supportPurposes: ["career"],
    };

    const profile = mapBackendProfileToFrontend(backend);

    expect(profile.countyCode).toBe("AB002");
    expect(profile.lifeSituations).toEqual(["employed"]);
    expect(profile.supportPurposes).toEqual(["career"]);
  });

  it("handles empty arrays for list fields", () => {
    const backend = {
      id: 3,
      name: "Empty Arrays",
    };

    const profile = mapBackendProfileToFrontend(backend);
    expect(profile.lifeSituations).toEqual([]);
    expect(profile.healthConditions).toEqual([]);
    expect(profile.supportPurposes).toEqual([]);
    expect(profile.occupations).toEqual([]);
  });
});

describe("mapFrontendProfileToBackend", () => {
  it("maps frontend profile to backend format", () => {
    const frontend = {
      id: 1,
      name: "Test Profile",
      isDefault: true,
      countyCode: "AB001",
      municipalityCode: "AB001",
      lifeSituations: ["student"],
      healthConditions: ["asthma"],
      healthDetails: "Mild",
      occupations: ["student"],
      supportPurposes: ["education"],
      legacyData: { source: "test" },
    };

    const backend = mapFrontendProfileToBackend(frontend);

    expect(backend.name).toBe("Test Profile");
    expect(backend.is_default).toBe(true);
    expect(backend.countyCode).toBe("AB001");
    expect(backend.municipalityCode).toBe("AB001");
    expect(backend.lifeSituations).toEqual(["student"]);
    expect(backend.healthConditions).toEqual(["asthma"]);
    expect(backend.healthDetails).toBe("Mild");
    expect(backend.occupations).toEqual(["student"]);
    expect(backend.supportPurposes).toEqual(["education"]);
    expect(backend.legacyData).toEqual({ source: "test" });
  });

  it("handles profile with undefined optional fields", () => {
    const frontend = {
      id: 1,
      name: "Minimal",
    };

    const backend = mapFrontendProfileToBackend(frontend);
    expect(backend.is_default).toBeUndefined();
    expect(backend.healthDetails).toBeUndefined();
    expect(backend.lifeSituations).toEqual([]);
    expect(backend.healthConditions).toEqual([]);
    expect(backend.supportPurposes).toEqual([]);
    expect(backend.occupations).toEqual([]);
  });
});
