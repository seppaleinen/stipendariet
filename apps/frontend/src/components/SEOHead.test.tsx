import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import SEOHead from "./SEOHead";

// Mock react-router-dom with configurable useLocation pathname
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return {
    ...actual,
    useLocation: () => ({ pathname: "/" }),
  };
});

// The global Helmet mock in test-setup.ts renders children inline,
// so JSON-LD scripts appear directly in the document.

function getJsonLdScripts(): HTMLScriptElement[] {
  return Array.from(
    document.querySelectorAll('script[type="application/ld+json"]')
  ) as HTMLScriptElement[];
}

function parseJsonLd(script: HTMLScriptElement) {
  return JSON.parse(script.textContent ?? "");
}

describe("SEOHead", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset useLocation to default "/" before each test
    vi.doMock("react-router-dom", async (importOriginal) => {
      const actual = await importOriginal<typeof import("react-router-dom")>();
      return {
        ...actual,
        useLocation: () => ({ pathname: "/" }),
      };
    });
  });

  it("renders two JSON-LD script tags", () => {
    render(<SEOHead />);

    const scripts = getJsonLdScripts();
    expect(scripts).toHaveLength(2);
  });

  it("emits valid JSON in both scripts", () => {
    render(<SEOHead />);

    for (const script of getJsonLdScripts()) {
      expect(() => parseJsonLd(script)).not.toThrow();
    }
  });

  it("includes Organization structured data", () => {
    render(<SEOHead />);

    const org = getJsonLdScripts()
      .map(parseJsonLd)
      .find((schema) => schema["@type"] === "Organization");

    expect(org).toBeDefined();
    expect(org["@context"]).toBe("https://schema.org");
    expect(org.name).toBe("StipendieAssistenten");
    expect(org.url).toBe("https://stipendieassistenten.labb.site");
    expect(org.slogan).toBe("Hitta och ansök om stipendier");
    expect(org.description).toContain("stipendier");
  });

  it("includes WebSite structured data with SearchAction", () => {
    render(<SEOHead />);

    const website = getJsonLdScripts()
      .map(parseJsonLd)
      .find((schema) => schema["@type"] === "WebSite");

    expect(website).toBeDefined();
    expect(website["@context"]).toBe("https://schema.org");
    expect(website.name).toBe("StipendieAssistenten");
    expect(website.potentialAction["@type"]).toBe("SearchAction");
    expect(website.potentialAction.target.urlTemplate).toBe(
      "https://stipendieassistenten.labb.site/grants?q={search_term_string}"
    );
    expect(website.potentialAction["query-input"]).toBe(
      "required name=search_term_string"
    );
  });

  it("Organization.sameAs contains only verified GitHub URL", () => {
    render(<SEOHead />);

    const org = getJsonLdScripts()
      .map(parseJsonLd)
      .find((schema) => schema["@type"] === "Organization");

    expect(org.sameAs).toEqual(["https://github.com/seppaleinen/stipendariet"]);
  });

  it("Organization includes Knowledge Graph fields (contactPoint, knowsLanguage)", () => {
    render(<SEOHead />);

    const org = getJsonLdScripts()
      .map(parseJsonLd)
      .find((schema) => schema["@type"] === "Organization");

    expect(org.contactPoint).toBeDefined();
    expect(org.contactPoint["@type"]).toBe("ContactPoint");
    expect(org.contactPoint.contactType).toBe("customer support");
    expect(org.contactPoint.availableLanguage).toEqual(["Swedish", "English"]);

    expect(org.knowsLanguage).toHaveLength(2);
    expect(org.knowsLanguage[0]).toEqual({ "@type": "Language", name: "Swedish", alternateName: "sv" });
  });

  it("suppresses Organization+WebSite schemas on /grants/:id paths", async () => {
    // Override useLocation mock for this test
    vi.doMock("react-router-dom", async (importOriginal) => {
      const actual = await importOriginal<typeof import("react-router-dom")>();
      return {
        ...actual,
        useLocation: () => ({ pathname: "/grants/grant-123" }),
      };
    });

    // Re-import SEOHead to pick up the new mock
    vi.resetModules();
    const { default: SEOHeadDyn } = await import("./SEOHead");

    render(<SEOHeadDyn />);

    const scripts = getJsonLdScripts();
    expect(scripts).toHaveLength(0);
  });

  it("renders Organization+WebSite on non-grant-detail paths", async () => {
    vi.doMock("react-router-dom", async (importOriginal) => {
      const actual = await importOriginal<typeof import("react-router-dom")>();
      return {
        ...actual,
        useLocation: () => ({ pathname: "/matching" }),
      };
    });

    vi.resetModules();
    const { default: SEOHeadDyn } = await import("./SEOHead");

    render(<SEOHeadDyn />);

    const scripts = getJsonLdScripts();
    expect(scripts).toHaveLength(2);

    const org = scripts.map(parseJsonLd).find((s) => s["@type"] === "Organization");
    expect(org).toBeDefined();
  });
});
