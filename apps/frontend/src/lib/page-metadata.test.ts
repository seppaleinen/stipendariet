import { describe, it, expect, vi, beforeEach } from "vitest";
import { getGrantMetadata, PAGE_METADATA, SITE_URL, DEFAULT_OG_IMAGE } from "@/lib/page-metadata";

describe("page-metadata constants", () => {
  it("SITE_URL is correct", () => {
    expect(SITE_URL).toBe("https://stipendieassistenten.labb.site");
  });

  it("DEFAULT_OG_IMAGE is correct", () => {
    expect(DEFAULT_OG_IMAGE).toBe(`${SITE_URL}/og-image.png`);
  });

  it("PAGE_METADATA contains all public routes", () => {
    const expectedRoutes = [
      "/",
      "/grants",
      "/matching",
      "/auth",
      "/applications",
      "/generate",
      "/profile-setup",
      "/family-setup",
    ];
    for (const route of expectedRoutes) {
      expect(PAGE_METADATA[route]).toBeDefined();
    }
  });

  it("PAGE_METADATA has correct title for home page", () => {
    expect(PAGE_METADATA["/"].title).toBe("StipendieAssistenten - Hitta och ansök om stipendier");
  });

  it("PAGE_METADATA has correct description for grants page", () => {
    expect(PAGE_METADATA["/grants"].description).toContain("hundratals");
  });

  it("PAGE_METADATA includes ogImage for all pages", () => {
    for (const [route, metadata] of Object.entries(PAGE_METADATA)) {
      expect(metadata.ogImage).toBe(DEFAULT_OG_IMAGE);
    }
  });
});

describe("getGrantMetadata", () => {
  const baseGrant = {
    title: "Test Grant",
    provider: "Test Provider",
    category: "Education",
    amount: "10000 SEK",
    description: "A test description",
    purpose: "Purpose text",
    translatedPurpose: "Translated purpose text",
  };

  it("returns correct title format", () => {
    const metadata = getGrantMetadata(baseGrant);
    expect(metadata.title).toBe("Test Grant - Test Provider | StipendieAssistenten");
  });

  it("uses translatedPurpose for description when available", () => {
    const metadata = getGrantMetadata(baseGrant);
    expect(metadata.description).toBe("Translated purpose text");
  });

  it("truncates description if longer than 155 chars", () => {
    const longGrant = {
      ...baseGrant,
      translatedPurpose: "A".repeat(200),
    };
    const metadata = getGrantMetadata(longGrant);
    expect(metadata.description.length).toBe(155); // 152 + "..."
    expect(metadata.description.endsWith("...")).toBe(true);
  });

  it("uses purpose when translatedPurpose is empty", () => {
    const grant = { ...baseGrant, translatedPurpose: "" };
    const metadata = getGrantMetadata(grant);
    expect(metadata.description).toBe("Purpose text");
  });

  it("uses description when both purpose and translatedPurpose are empty", () => {
    const grant = { ...baseGrant, purpose: "", translatedPurpose: "" };
    const metadata = getGrantMetadata(grant);
    expect(metadata.description).toBe("A test description");
  });

  it("includes ogImage and canonicalUrl", () => {
    const metadata = getGrantMetadata(baseGrant);
    expect(metadata.ogImage).toBe(DEFAULT_OG_IMAGE);
    expect(metadata.canonicalUrl).toBe(`${SITE_URL}/grants`);
  });

  it("handles grant without optional fields", () => {
    const minimalGrant = {
      title: "Minimal",
      provider: "Provider",
      category: "Other",
    };
    const metadata = getGrantMetadata(minimalGrant);
    expect(metadata.description).toBe("");
    expect(metadata.title).toBe("Minimal - Provider | StipendieAssistenten");
  });
});
