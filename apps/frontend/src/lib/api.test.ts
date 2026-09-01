import { describe, it, expect } from "vitest";
import {
  mapGrantFromBackend,
  mapApplicationFromBackend,
  mapBackendProfileToFrontend,
  mapFrontendProfileToBackend,
  mapMatchedFoundations,
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

  it("maps enrichment fields", () => {
    const backend: Record<string, unknown> = {
      id: "123",
      name: "Test",
      website_url: "https://stiftelse.se",
      application_deadline: "2026-03-31",
      application_start: "2026-01-15",
      application_method: "Ansök via e-post",
      contact_email: "info@stiftelse.se",
      contact_phone: "08-987654",
      who_can_apply: "Studerande med fullständiga betyg",
    };

    const grant = mapGrantFromBackend(backend);

    expect(grant.websiteUrl).toBe("https://stiftelse.se");
    expect(grant.applicationDeadline).toBe("2026-03-31");
    expect(grant.applicationStart).toBe("2026-01-15");
    expect(grant.applicationMethod).toBe("Ansök via e-post");
    expect(grant.contactEmail).toBe("info@stiftelse.se");
    expect(grant.contactPhone).toBe("08-987654");
    expect(grant.whoCanApply).toBe("Studerande med fullständiga betyg");
  });

  // GEO Flaw #1 — verify enrichedDescription is mapped and used in descriptionText (issue #2)
  it("maps enrichedDescription from backend", () => {
    const backend: Record<string, unknown> = {
      id: "123",
      name: "Uppsala Stipendiet",
      enriched_description:
        "Detta stipendium stödjer universitetsstuderande i Uppsala. "
        + "Behöriga är studenter vid Uppsala universitet som är i behov av "
        + "ekonomiskt stöd för att kunna genomföra sina studier. "
        + "Bidraget kan användas för att täcka kurslitteratur, resor samt "
        + "levnadskostnader. Sökande bör bifoga studieintyg och motivering.",
    };

    const grant = mapGrantFromBackend(backend);

    expect(grant.enrichedDescription).toBe(
      "Detta stipendium stödjer universitetsstuderande i Uppsala. "
        + "Behöriga är studenter vid Uppsala universitet som är i behov av "
        + "ekonomiskt stöd för att kunna genomföra sina studier. "
        + "Bidraget kan användas för att täcka kurslitteratur, resor samt "
        + "levnadskostnader. Sökande bör bifoga studieintyg och motivering."
    );
  });

  it("leaves enrichedDescription undefined when missing", () => {
    const backend: Record<string, unknown> = {
      id: "123",
      name: "Test",
    };

    const grant = mapGrantFromBackend(backend);
    expect(grant.enrichedDescription).toBeUndefined();
  });

  it("leaves enrichment fields undefined when missing", () => {
    const backend: Record<string, unknown> = {
      id: "123",
      name: "Test",
    };

    const grant = mapGrantFromBackend(backend);
    expect(grant.applicationDeadline).toBeUndefined();
    expect(grant.applicationStart).toBeUndefined();
    expect(grant.applicationMethod).toBeUndefined();
    expect(grant.contactEmail).toBeUndefined();
    expect(grant.contactPhone).toBeUndefined();
    expect(grant.whoCanApply).toBeUndefined();
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

  it("maps self_description snake_case to selfDescription", () => {
    const backend = {
      id: 4,
      name: "With Description",
      self_description: "Jag är student och söker stöd.",
    };

    const profile = mapBackendProfileToFrontend(backend);
    expect(profile.selfDescription).toBe("Jag är student och söker stöd.");
  });

  it("maps selfDescription camelCase as fallback source", () => {
    const backend = {
      id: 5,
      name: "Camel Description",
      selfDescription: "Beskrivning på egna ord.",
    };

    const profile = mapBackendProfileToFrontend(backend);
    expect(profile.selfDescription).toBe("Beskrivning på egna ord.");
  });

  it("leaves selfDescription undefined when missing", () => {
    const backend = {
      id: 6,
      name: "No Description",
    };

    const profile = mapBackendProfileToFrontend(backend);
    expect(profile.selfDescription).toBeUndefined();
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

  it("maps selfDescription to backend payload", () => {
    const frontend = {
      id: 2,
      name: "With Self-description",
      selfDescription: "Ensamma föräldern söker stöd.",
    };

    const backend = mapFrontendProfileToBackend(frontend);
    expect(backend.selfDescription).toBe("Ensamma föräldern söker stöd.");
  });

  it("round-trips selfDescription through both mappers", () => {
    const backendInput = {
      id: 3,
      name: "Round Trip",
      self_description: "Text som ska bevaras.",
    };

    const frontend = mapBackendProfileToFrontend(backendInput);
    expect(frontend.selfDescription).toBe("Text som ska bevaras.");

    const backendOutput = mapFrontendProfileToBackend(frontend);
    expect(backendOutput.selfDescription).toBe("Text som ska bevaras.");
  });
});

describe("mapMatchedFoundations", () => {
  it("maps parsed_service_area to parsedServiceArea on the foundation", () => {
    const backend = [
      {
        foundation: {
          id: 1,
          foundation_id: 100,
          name: "Kalmar Stiftelse",
          summary: "Stöd i sydöstra Sverige.",
          translated_purpose: "Stöd för studier i Kalmar.",
          category: "Education",
          parsed_service_area: {
            municipality_code: "0880",
            county_code: "08",
            municipality_name: "Kalmar",
            county_name: "Kalmar län",
            source_text: "Kalmar",
            confidence: "high",
            service_area_detail: "Området runt Kalmar stad",
          },
        },
        similarity_score: 0.87,
      },
    ];

    const mapped = mapMatchedFoundations(backend);

    expect(mapped[0].foundation.parsedServiceArea).toEqual({
      municipality_code: "0880",
      county_code: "08",
      municipality_name: "Kalmar",
      county_name: "Kalmar län",
      source_text: "Kalmar",
      confidence: "high",
      service_area_detail: "Området runt Kalmar stad",
    });
    // snake_case key is removed; other foundation fields are preserved
    expect((mapped[0].foundation as Record<string, unknown>).parsed_service_area).toBeUndefined();
    expect(mapped[0].foundation.name).toBe("Kalmar Stiftelse");
    expect(mapped[0].foundation.category).toBe("Education");
    expect(mapped[0].similarity_score).toBe(0.87);
  });

  it("leaves parsedServiceArea undefined when parsed_service_area is absent", () => {
    const backend = [
      {
        foundation: {
          id: 2,
          foundation_id: 200,
          name: "Stiftelse utan service area",
          summary: null,
          translated_purpose: "Allmännyttigt ändamål.",
          category: null,
        },
        similarity_score: 0.5,
      },
    ];

    const mapped = mapMatchedFoundations(backend);

    expect(mapped[0].foundation.parsedServiceArea).toBeUndefined();
    expect(mapped[0].foundation.name).toBe("Stiftelse utan service area");
    expect(mapped[0].similarity_score).toBe(0.5);
  });
});
