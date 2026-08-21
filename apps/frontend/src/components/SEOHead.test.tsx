import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import SEOHead from "./SEOHead";

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
});
