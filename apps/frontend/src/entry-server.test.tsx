/**
 * SEO smoke tests for the SSR render pipeline (entry-server.tsx — the same
 * entry scripts/ssr-server.js loads for on-demand /grants/<id> rendering).
 *
 * No live backend / cluster needed: `render()` is called directly with a
 * mocked grant seeded via SSRData (exactly what the sidecar does after
 * fetching from the API and mapping through mapGrantFromBackend()).
 *
 * This file runs in a NODE environment (// @vitest-environment node), not
 * jsdom. Reason: react-helmet-async@3.0.0 captures `canUseDOM` at module-eval
 * from `window.document.createElement`. Under jsdom that is truthy, so the lib
 * runs in client mode where SSR head extraction (`helmetContext.helmet`) is
 * skipped — head output is always empty in jsdom. Under plain Node (the
 * production SSR environment) it flips to server mode and extracts head
 * correctly. The setup file (test-setup.ts) is guarded accordingly, and the
 * global react-helmet-async / react-router-dom mocks are unmocked here so the
 * REAL modules run — i.e. this exercises the actual production render path.
 */
// @vitest-environment node
import { describe, it, expect, vi } from "vitest";

vi.unmock("react-helmet-async");
vi.unmock("react-router-dom");

import { render } from "./entry-server";

const SITE_URL = "https://stipendieassistenten.labb.site";

// Mirrors the shape produced by scripts/ssr-server.js mapGrantFromBackend().
const ssrGrant = {
  id: "foundation-ssr-1",
  title: "Södermanlands Kulturstipendium",
  provider: "Södermanlands Stiftelse",
  summary: "Ett stipendium för kulturarbetare i Södermanland.",
  category: "Kultur",
  tags: ["kultur", "konst", "södermanland"],
  isRecurring: true,
  purpose: "Stöd för kulturarbetare.",
  // 300+ chars — forces description capping into the 120-155 SEO range.
  enrichedDescription:
    "Detta stipendium stödjer yrkesverksamma kulturarbetare i Södermanland " +
    "som är i behov av ekonomiskt stöd för sina projekt. Bidraget kan användas " +
    "för ateljéhyra, material, resor och levnadskostnader under projektperioden. " +
    "Sökande bör bifoga en projektbeskrivning, en budget samt en tydlig redogörelse " +
    "för hur bidraget bidrar till regionens kulturliv. Stipendiet utlyses årligen " +
    "och beslut meddelas senast åtta veckor efter sista ansökningsdag.",
  deadline: "2026-10-01",
  applicationStart: "2026-01-01",
  applicationDeadline: "2026-05-15",
  whoCanApply: "Yrkesverksamma kulturarbetare folkbokförda i Södermanland.",
};

/** Extract a named attribute value from a single serialized tag string. */
function attr(tag: string, name: string) {
  return tag.match(new RegExp(`${name}="([^"]*)"`))?.[1] ?? "";
}

/** Find the first <meta ...> tag carrying the given attribute=value pair. */
function findMeta(head: string, attrName: string, attrValue: string) {
  const re = new RegExp(`<meta[^>]*${attrName}="${attrValue}"[^>]*>`, "g");
  return head.match(re)?.[0] ?? "";
}

/** Parse every application/ld+json script in the serialized head. */
function parseLdJson(head: string) {
  const re = /<script[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g;
  const blocks: Record<string, unknown>[] = [];
  for (const m of head.matchAll(re)) {
    try {
      blocks.push(JSON.parse(m[1]));
    } catch {
      // ignore malformed — the assertions below surface what is missing
    }
  }
  return blocks;
}

describe("SSR render() — /grants/:id SEO smoke (real server path, no live backend)", () => {
  const url = `/grants/${ssrGrant.id}`;

  it("renders full grant HTML (not an empty SPA shell)", async () => {
    const { html } = await render(url, { grant: ssrGrant });

    // Body content is actually rendered — a crawler sees the grant, not a shell.
    expect(html).toContain("Södermanlands Kulturstipendium");
    expect(html).toContain("Södermanlands Stiftelse");
  });

  it("emits a unique <title> for the grant", async () => {
    const { head } = await render(url, { grant: ssrGrant });

    const title = head.match(/<title[^>]*>([\s\S]*?)<\/title>/)?.[1] ?? "";
    expect(title).toContain(ssrGrant.title);
    expect(title).toContain(ssrGrant.provider);
    expect(title).toContain("StipendieAssistenten");
  });

  it("emits a description meta capped into 120-155 chars", async () => {
    const { head } = await render(url, { grant: ssrGrant });

    const content = attr(findMeta(head, "name", "description"), "content");
    expect(content.length).toBeGreaterThanOrEqual(120);
    expect(content.length).toBeLessThanOrEqual(155);
    expect(content.endsWith("...")).toBe(true);
    // Capped version is derived from the enriched description.
    expect(content.slice(0, 152)).toBe(ssrGrant.enrichedDescription.slice(0, 152));
  });

  it("emits og:*, twitter:card/site and canonical pointing at the grant URL", async () => {
    const { head } = await render(url, { grant: ssrGrant });

    expect(attr(findMeta(head, "property", "og:title"), "content")).toContain(ssrGrant.title);
    expect(attr(findMeta(head, "property", "og:description"), "content")).toContain("stipendium");
    expect(attr(findMeta(head, "property", "og:image"), "content")).toBe(`${SITE_URL}/og-image.png`);
    expect(attr(findMeta(head, "property", "og:url"), "content")).toBe(`${SITE_URL}${url}`);
    expect(attr(findMeta(head, "name", "twitter:card"), "content")).toBe("summary_large_image");
    expect(attr(findMeta(head, "name", "twitter:site"), "content")).toBe("@StipendieAss");
    expect(head).toContain(`rel="canonical"`);
    expect(head).toContain(`${SITE_URL}${url}`);
  });

  it("emits ScholarshipProgram and BreadcrumbList JSON-LD blocks", async () => {
    const { head } = await render(url, { grant: ssrGrant });

    const blocks = parseLdJson(head);
    const scholarship = blocks.find((b) => b["@type"] === "ScholarshipProgram");
    const breadcrumb = blocks.find((b) => b["@type"] === "BreadcrumbList");

    expect(scholarship).toBeDefined();
    expect((scholarship as { name?: string }).name).toBe(ssrGrant.title);
    expect((scholarship as { inLanguage?: string }).inLanguage).toBe("sv-SE");

    expect(breadcrumb).toBeDefined();
    const items = (breadcrumb as { itemListElement?: unknown[] })?.itemListElement ?? [];
    expect(items).toHaveLength(3);
    expect((items[2] as { name?: string }).name).toBe(ssrGrant.title);
  });
});

describe("SSR render() — /matching public route Helmet output", () => {
  it("emits matching title, description, canonical, og and twitter tags", async () => {
    const { head } = await render("/matching");

    const title = head.match(/<title[^>]*>([\s\S]*?)<\/title>/)?.[1] ?? "";
    expect(title).toBe("Matcha dina behov med rätt stipendier | StipendieAssistenten");

    const description = attr(findMeta(head, "name", "description"), "content");
    expect(description).toContain("matchar dina och din familjs behov");

    expect(attr(findMeta(head, "property", "og:title"), "content")).toBe(
      "Matcha dina behov med rätt stipendier | StipendieAssistenten"
    );
    expect(attr(findMeta(head, "property", "og:image"), "content")).toBe(`${SITE_URL}/og-image.png`);
    expect(attr(findMeta(head, "property", "og:url"), "content")).toBe(`${SITE_URL}/matching`);
    expect(attr(findMeta(head, "name", "twitter:card"), "content")).toBe("summary_large_image");
    expect(attr(findMeta(head, "name", "twitter:site"), "content")).toBe("@StipendieAss");
    expect(head).toContain(`rel="canonical"`);
    expect(head).toContain(`${SITE_URL}/matching`);
  });
});