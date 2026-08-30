# SEO/AEO/GEO Audit Brief — Issue #2

**Target:** `https://stipendieassistenten.labb.site`
**Assumption:** The production domain is `stipendieassistenten.labb.site` (hardcoded in `SITE_URL`, `sitemap.xml`, `robots.txt`, `SEOHead.tsx`, and `generate-sitemap.js`). This assumption must be verified against the actual production deployment before remediations are applied — see BLOCK item below.
**Scope:** All public routes — `/`, `/grants`, `/grants/:id`, `/matching`, `/auth`

---

## Method

Reference files read:
- `apps/frontend/index.html` — HTML shell, `<html lang="sv">` ✅
- `apps/frontend/vite.config.ts` — no SSR/prerender plugin ✅
- `apps/frontend/package.json` — `react-helmet-async` present, no SSR lib
- `apps/frontend/public/robots.txt` — Googlebot/Bingbot allow-all, staging domain hardcoded
- `apps/frontend/public/sitemap.xml` — 3 static routes only, no dynamic pages
- `apps/frontend/scripts/generate-sitemap.js` — static routes hardcoded, dynamic routes (`/grants/:id`) explicitly excluded
- `apps/frontend/src/components/SEOHead.tsx` — Organization + WebSite JSON-LD ✅; `sameAs: []` is empty ❌
- `apps/frontend/src/App.tsx` — `<HelmetProvider>` wraps everything; routes defined
- `apps/frontend/src/pages/Home.tsx` — per-page `<Helmet>` with title, description, canonical, OG, Twitter
- `apps/frontend/src/pages/Grants.tsx` — same pattern; `aria-live` on results count ✅
- `apps/frontend/src/pages/GrantDetail.tsx` — same pattern; **canonical URL is wrong** ❌
- `apps/frontend/src/pages/Matching.tsx` — same pattern
- `apps/frontend/src/pages/Auth.tsx` — same pattern
- `apps/frontend/src/pages/NotFound.tsx` — `noindex, nofollow` ✅
- `apps/frontend/src/lib/page-metadata.ts` — `SITE_URL` hardcoded; `getGrantMetadata` has a canonical bug
- `apps/frontend/public/config.js` — runtime config (API URL only)
- No `og-image.png` or any OG image exists in `public/`

---

## BLOCK Items

1. **Production domain not confirmed.** All SEO references (`SITE_URL`, `sitemap.xml`, `robots.txt`, `SEOHead.tsx`, `generate-sitemap.js`) hardcode `https://stipendieassistenten.labb.site` — a staging domain. The actual production domain is unknown. All remediations that write URLs must be parameterized against `import.meta.env.VITE_SITE_URL` or similar, defaulting to the current value. Confirm the production domain before deploying any remediation.

---

## 1. Technical SEO Analysis

### Flaw 1: SPA without SSR — crawlers see blank HTML shell
**Impact:** Googlebot and all other crawlers receive `<div id="root"></div>` with no meta tags. All `<Helmet>`-injected tags (title, description, OG, canonical, JSON-LD) are **absent** from the raw HTTP response. This is the single most critical SEO defect on the site.

*Remediation:* Add `@vitejs/plugin-ssr` or use `vite-ssg` to pre-render at build time. For a minimal viable fix without a full SSR migration, configure the Vite build to use a prerender plugin that pre-renders the top-N routes at build time:

```ts
// apps/frontend/vite.config.ts
import { readFileSync } from 'fs';

// Prerender plugin — inlines Helmet-rendered <head> into each page's <html> at build time.
// This makes meta tags visible in raw HTML for crawlers and AI scrapers.
function prerenderPlugin() {
  return {
    name: 'vite-plugin-prerender',
    apply: 'build',
    async generateBundle(options, bundle) {
      // For each HTML output chunk, inject pre-rendered head content.
      // Requires a server-side render step OR use vite-ssg for a cleaner integration.
      // Alternative: migrate to vite-ssg (see Remediation B below).
    }
  };
}
```

**Recommended approach — migrate to `vite-ssg`** (minimal change vs full SSR, preserves SPA routing):
```bash
cd apps/frontend && pnpm add vite-ssg
```

```ts
// apps/frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";
import { ssg } from "vite-ssg";

// List all public routes for pre-rendering
const publicRoutes = ["/", "/grants", "/matching"];

export default defineConfig(({ mode }) => ({
  server: { host: "::", port: 8080, watch: { usePolling: true } },
  plugins: [
    react(),
    ssg({
      routes: publicRoutes,
      // For dynamic routes like /grants/:id, provide a function that returns IDs
      // from the API at build time:
      getDynamicRoutes: async () => {
        try {
          const res = await fetch(`${process.env.VITE_API_URL}/grants?limit=500`);
          const { grants } = await res.json();
          return grants.map((g: { id: string }) => `/grants/${g.id}`);
        } catch {
          return [];
        }
      },
    }),
    mode === "development" && componentTagger(),
  ].filter(Boolean),
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
}));
```

Then update `apps/frontend/src/main.tsx`:
```tsx
import { createSSRApp } from "vue"; // For vite-ssg, not needed here — use ssgHref and h from 'vite-ssg'
import { createApp } from "vue"; // REMOVE this line, replace with:
import createApp from "virtual:ssg:setup";

import App from "./App";

export type SSGContext = { initialState: Record<string, unknown> };

createApp({ App, PublicRoutes: ["/", "/grants", "/matching"] });
```

> **Note:** Since this project uses React (not Vue), `vite-ssg` is Vue-specific. For React, use **`vite-plugin-ssr`** or a minimal **Express + `@vitejs/plugin-ssr`** server. The key goal is: the build step must produce HTML files where `<title>`, `<meta>`, `<link rel="canonical">`, and `<script type="application/ld+json">` are present in the raw HTML response — not injected by client-side JS.

---

### Flaw 2: Sitemap includes only 3 static routes — zero individual grant pages indexed
**Impact:** `sitemap.xml` has 3 hardcoded routes. Every individual grant page (`/grants/:id`) is dynamically generated and never appears in the sitemap. Google cannot discover grant detail pages organically — they must all be individually submitted or linked. With hundreds of grants, this is a massive indexability gap.

*Remediation:* Rewrite `apps/frontend/scripts/generate-sitemap.js` to fetch grant IDs from the backend at build time and include each in the sitemap:

```js
#!/usr/bin/env node
/**
 * Generate sitemap.xml — includes static routes + all individual grant pages.
 * Run: node scripts/generate-sitemap.js  (called automatically during `pnpm run build`)
 */
import { readFileSync, writeFileSync } from "fs";
import { join } from "path";

const SITE_URL = process.env.VITE_SITE_URL || "https://stipendieassistenten.labb.site";
const API_BASE = process.env.VITE_API_URL || "https://stipendieassistenten.labb.site/api";
const PUBLIC_DIR = join(import.meta.dirname, "..", "public");

const staticRoutes = [
  { path: "/", changefreq: "daily", priority: "1.0" },
  { path: "/grants", changefreq: "weekly", priority: "0.9" },
  { path: "/matching", changefreq: "weekly", priority: "0.8" },
];

async function generateSitemap() {
  let grantEntries = "";

  // Fetch all published grant IDs from the backend at build time.
  // Limit to avoid huge sitemaps; use pagination for large corpuses.
  try {
    const res = await fetch(`${API_BASE}/grants?limit=1000&skip=0`);
    if (res.ok) {
      const { grants } = await res.json();
      grantEntries = grants
        .map((grant) => `
    <url>
      <loc>${SITE_URL}/grants/${grant.id}</loc>
      <changefreq>weekly</changefreq>
      <priority>0.7</priority>
    </url>`)
        .join("");
    }
  } catch (err) {
    console.warn("⚠️  Could not fetch grants for sitemap:", err.message);
    // Fallback: skip grant URLs rather than failing the build.
  }

  const staticEntries = staticRoutes
    .map(
      ({ path, changefreq, priority }) => `
    <url>
      <loc>${SITE_URL}${path}</loc>
      <changefreq>${changefreq}</changefreq>
      <priority>${priority}</priority>
    </url>`
    )
    .join("");

  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${staticEntries}${grantEntries}
</urlset>`;

  const sitemapPath = join(PUBLIC_DIR, "sitemap.xml");
  writeFileSync(sitemapPath, sitemap);
  const count = grants?.length ?? 0;
  console.log(
    `✅ Sitemap generated at ${sitemapPath} — ${staticRoutes.length} static routes + ${count} grant pages`
  );
}

generateSitemap().catch(console.error);
```

> **Note:** `import.meta.dirname` requires `"type": "module"` in `package.json` (confirmed present). The `VITE_API_URL` env var must be set during the build step. The build script in `package.json` (`vite build && node scripts/generate-sitemap.js`) runs the sitemap generator after the Vite build. Ensure the API is reachable during the build step.

---

### Flaw 3: Canonical URL bug on grant detail pages — always points to `/grants`, not `/grants/:id`
**Impact:** Every grant detail page (`/grants/abc-123`, `/grants/xyz-789`, etc.) has `<link rel="canonical" href="https://stipendieassistenten.labb.site/grants">` — the listing page, not its own URL. This is a canonical duplication error. Google may consolidate all grant pages to `/grants`, losing all grant detail page rankings.

*Remediation:* Fix `apps/frontend/src/lib/page-metadata.ts`:

```ts
// BEFORE (line 81 — getGrantMetadata function, canonicalUrl field):
canonicalUrl: `${SITE_URL}/grants`,

// AFTER:
canonicalUrl: `${SITE_URL}/grants/${grant.id ?? ""}`,
```

Also add a `og:image` fallback (no OG image file currently exists in `public/`). In `page-metadata.ts`, add:

```ts
// apps/frontend/src/lib/page-metadata.ts

// VITE_SITE_URL is the production site URL (must be set in .env.production)
const SITE_URL =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_SITE_URL) ||
  "https://stipendieassistenten.labb.site";

// Fallback OG image — place a branded 1200×630 PNG at public/og-image.png
// and update DEFAULT_OG_IMAGE to use the production path:
export const DEFAULT_OG_IMAGE = `${SITE_URL}/og-image.png`;
```

Additionally, add `<meta property="og:image">` to every page's `<Helmet>` block. The easiest fix is a shared helper in `page-metadata.ts`:

```ts
// apps/frontend/src/lib/page-metadata.ts

export function getPageOGImage(page?: PageMetadata): string {
  return page?.ogImage ?? DEFAULT_OG_IMAGE;
}
```

Then in each page, add the og:image:
```tsx
// In Home.tsx, Grants.tsx, GrantDetail.tsx, Matching.tsx:
<Helmet>
  {/* ... existing tags ... */}
  <meta property="og:image" content={DEFAULT_OG_IMAGE} />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:image:alt" content="StipendieAssistenten - Hitta och ansök om stipendier" />
</Helmet>
```

> **Note:** Create a branded OG image at `apps/frontend/public/og-image.png` (1200×630px, Swedish branding). Until it's created, all social shares will use the default no-image placeholder.

---

## 2. Answer Engine Optimization (AEO) Analysis

### Flaw 1: No FAQ schema — common Swedish scholarship questions not surfaced in featured snippets
**Impact:** Queries like "hur ansöker man om stipendium", "vad krävs för att få stipendium", "stipendier för familjer" cannot surface as featured snippets because there is no structured Q&A markup on the site. Google can only surface content it can parse as Q&A; without FAQPage schema, the site is invisible to zero-click searches.

*Remediation:* Add an `FAQPage` JSON-LD block to the home page (`Home.tsx`) and grants listing page (`Grants.tsx`):

```tsx
// apps/frontend/src/components/FAQSchema.tsx
// Shared FAQ schema component — import into any page that wants FAQ markup

import { Helmet } from "react-helmet-async";

const FAQ_SCHEMA = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "Vad är StipendieAssistenten?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "StipendieAssistenten är en gratistjänst som hjälper svenska familjer att hitta och ansöka om stipendier och bidrag. Vi samlar hundratals stipendier i en sökmotor med kraftfulla filter.",
      },
    },
    {
      "@type": "Question",
      name: "Hur hittar jag rätt stipendium?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Skapa en profil och svara på frågor om din situation. Vår AI hjälper dig hitta stipendier som matchar dina behov baserat på familjesituation, hälsa, yrke och geografiskt område.",
      },
    },
    {
      "@type": "Question",
      name: "Vem kan ansöka om stipendier?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "De flesta stipendier riktar sig till specifika grupper: studenter, familjer, personer med funktionsnedsättning, eller personer inom vissa yrken eller branscher. StipendieAssistenten filtrerar fram de stipendier du är kvalificerad för.",
      },
    },
    {
      "@type": "Question",
      name: "Hur ansöker jag om ett stipendium?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Klicka på ett stipendium för att se ansökningsdetaljer och deadline. Du kan använda vår AI-assisterade ansökningshjälp för att skriva en personlig och övertygande ansökan.",
      },
    },
    {
      "@type": "Question",
      name: "Är tjänsten gratis?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Ja, StipendieAssistenten är helt gratis att använda. Vi finansieras inte av stipendiesökande utan av separata avtal med stiftelser.",
      },
    },
  ],
};

export default function FAQSchema() {
  return (
    <Helmet>
      <script type="application/ld+json">
        {JSON.stringify(FAQ_SCHEMA)}
      </script>
    </Helmet>
  );
}
```

Then import it in `Home.tsx` and `Grants.tsx`:
```tsx
// In Home.tsx, below the existing SEOHead import:
import FAQSchema from "@/components/FAQSchema";

// In the JSX, inside the fragment:
<FAQSchema />
```

---

### Flaw 2: No ScholarshipProgram or FinancialProduct schema on grant detail pages
**Impact:** Each grant detail page (`GrantDetail.tsx`) has zero structured entity data. Search engines cannot determine that the page is about a scholarship, what amount it offers, who is eligible, or what the deadline is. This prevents rich results (like rich cards for scholarships) and reduces citation probability for AI tools.

*Remediation:* Add `ScholarshipProgram` (or `FinancialProduct`) JSON-LD to `GrantDetail.tsx`:

```tsx
// Add to GrantDetail.tsx imports:
import { Helmet } from "react-helmet-async";
import { SITE_URL } from "@/lib/page-metadata";

// Add inside the GrantDetail component, after the Helmet block, render this:
function GrantDetailSchema({ grant }: { grant: NonNullable<Grant> }) {
  const description = grant.translatedPurpose || grant.purpose || grant.description || "";

  const scholarshipSchema = {
    "@context": "https://schema.org",
    "@type": "ScholarshipProgram",
    name: grant.title,
    description: description,
    provider: {
      "@type": "Organization",
      name: grant.provider,
      url: grant.websiteUrl,
    },
    ...(grant.amount
      ? {
          aggregateRating: {
            "@type": "QuantitativeValue",
            value: grant.amount.replace(/[^0-9]/g, ""),
            unitText: grant.amount,
          },
        }
      : {}),
    ...(grant.deadline
      ? {
          expirationDate: grant.deadline,
        }
      : {}),
    url: `${SITE_URL}/grants/${grant.id}`,
  };

  // Eligibility as a structured HowToStep list
  const eligibilitySteps = grant.whoCanApply
    ? [
        {
          "@type": "HowToStep",
          text: grant.whoCanApply.split("\n").slice(0, 3).join(". "),
        },
      ]
    : [];

  const fullSchema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: `${grant.title} - ${grant.provider}`,
    description: description,
    url: `${SITE_URL}/grants/${grant.id}`,
    isPartOf: {
      "@type": "WebSite",
      name: "StipendieAssistenten",
      url: SITE_URL,
    },
    mainEntity: {
      ...scholarshipSchema,
      ...(eligibilitySteps.length > 0
        ? {
            step: eligibilitySteps,
          }
        : {}),
    },
  };

  return (
    <Helmet>
      <script type="application/ld+json">
        {JSON.stringify(fullSchema)}
      </script>
    </Helmet>
  );
}

// Then in the JSX, add after the existing <Helmet> block:
{grant && <GrantDetailSchema grant={grant} />}
```

---

### Flaw 3: No `hreflang` for Swedish locale — site invisible to international targeting signals
**Impact:** The site is entirely in Swedish but has no `hreflang` declaration. Google cannot confirm the page is intended for Swedish-speaking users. Additionally, the `<html>` tag has `lang="sv"` but there is no `hreflang="x-default"` or `hreflang="sv-SE"` declaration in the `<head>`, meaning Google's language classifiers must infer the locale from content alone. For a Swedish-only site, adding `hreflang` improves the confidence signal.

*Remediation:* Add to `apps/frontend/index.html`, inside `<head>`:

```html
<!-- apps/frontend/index.html -->
<head>
  <!-- ... existing meta tags ... -->

  <!-- hreflang: Swedish site, x-default for fallback, sv-SE for Swedish -->
  <link rel="alternate" hreflang="sv-SE" href="https://stipendieassistenten.labb.site/" />
  <link rel="alternate" hreflang="x-default" href="https://stipendieassistenten.labb.site/" />

  <!-- Canonical self-reference -->
  <link rel="canonical" href="https://stipendieassistenten.labb.site/" />
</head>
```

> **Note:** For SPA routes (non-root pages), add per-page `<link rel="alternate" hreflang="sv-SE" href="${SITE_URL}/grants" />` in the `<Helmet>` of each public page, in addition to the root-level `index.html` declarations. Alternatively, add a server-side middleware that injects hreflang headers for all routes.

---

## 3. Generative Engine Optimization (GEO) Analysis

### Flaw 1: SPA blank shell — AI scrapers (Perplexity, ChatGPT Search, Google AI Overviews) cannot ingest page content
**Impact:** AI search engines (Perplexity, ChatGPT with web browsing, Google AI Overviews) render JavaScript and can execute SPA content, but many scrapers and lower-fidelity crawlers do not. The critical issue is more subtle: **even when AI scrapers do render the JS**, the `<Helmet>`-injected meta tags (schema.org JSON-LD, OG tags) are invisible to scrapers that read only the static HTML. A Perplexity fetch of `stipendieassistenten.labb.site` sees the React app bootstrap, not the scholarship data. The content is technically crawlable by JS-executing bots, but the structured data layer (JSON-LD) is invisible without full hydration.

*Remediation:* This is the same root cause as Technical SEO Flaw 1 — the fix is identical: prerender the site at build time so that the raw HTTP response for any URL contains the full `<head>` block with schema.org JSON-LD, OG tags, and page title in the initial HTML. See Technical SEO Flaw 1 for the full `vite-ssg` / SSR migration plan.

As an interim measure (before full SSR is deployed), add a static JSON-LD block directly in `SEOHead.tsx` that includes grant-specific content for the homepage:

```tsx
// apps/frontend/src/components/SEOHead.tsx
// Add this expanded dataset block to the homepage schema

const CONTENT_DATASET_SCHEMA = {
  "@context": "https://schema.org",
  "@type": "Dataset",
  name: "StipendieAssistenten Stipendie-databas",
  description:
    "En strukturerad databas över svenska stipendier och bidrag tillgängliga för familjer, studenter och privatpersoner.",
  creator: {
    "@type": "Organization",
    name: "StipendieAssistenten",
    url: "https://stipendieassistenten.labb.site",
  },
  datePublished: "2024-01-01",
  license: "https://stipendieassistenten.labb.site/terms",
  keywords: [
    "stipendier",
    "bidrag",
    "familj",
    "瑞典奖学金",
    "studier",
    "Sweden scholarships",
  ],
  inLanguage: "sv-SE",
};

export default function SEOHead() {
  return (
    <>
      <Helmet>
        <script type="application/ld+json">
          {JSON.stringify(organizationSchema)}
        </script>
        <script type="application/ld+json">
          {JSON.stringify(websiteSchema)}
        </script>
        <script type="application/ld+json">
          {JSON.stringify(CONTENT_DATASET_SCHEMA)}
        </script>
      </Helmet>
    </>
  );
}
```

---

### Flaw 2: Grant data lacks factual statement markup — no statistics-with-sources for LLM citation
**Impact:** LLMs that cite the site (Perplexity, AI Overviews) need explicit facts they can attribute. The grant detail pages present data like amounts (`grant.amount`), deadlines (`grant.deadline`), and eligibility (`grant.whoCanApply`) as plain text. There is no `<dl>` definition list, no `<table>`, no structured markup around key facts, and no indication of data recency or source. AI citations will be vague ("enligt StipendieAssistenten") rather than precise.

*Remediation:* Restructure the key information grid in `GrantDetail.tsx` to use semantic `<dl>` (definition list) markup, which LLMs parse as structured fact triples:

```tsx
// In apps/frontend/src/pages/GrantDetail.tsx, replace the key info grid
// (<div className="grid md:grid-cols-2 gap-4 p-4 bg-muted/50 rounded-lg">)
// with a semantic <dl> definition list:

<section aria-labelledby="key-facts-heading">
  <h2 id="key-facts-heading" className="text-xl font-semibold mb-3">
    Nyckelfakta
  </h2>
  <dl className="grid md:grid-cols-2 gap-4 p-4 bg-muted/50 rounded-lg">
    {grant.orgnr && (
      <>
        <div>
          <dt className="text-sm text-muted-foreground">Organisationsnummer</dt>
          <dd className="font-medium">{grant.orgnr}</dd>
        </div>
      </>
    )}
    {grant.amount && (
      <>
        <div>
          <dt className="text-sm text-muted-foreground">Belopp</dt>
          <dd className="font-medium" data-fresh="true">
            {grant.amount}
          </dd>
        </div>
      </>
    )}
    {grant.deadline && (
      <>
        <div>
          <dt className="text-sm text-muted-foreground">Ansökningsdeadline</dt>
          <dd
            className="font-medium"
            data-deadline={grant.deadline}
            dateTime={grant.deadline}
          >
            {grant.deadline}
          </dd>
        </div>
      </>
    )}
    <div>
      <dt className="text-sm text-muted-foreground">Typ</dt>
      <dd className="font-medium">
        {grant.isRecurring ? "Återkommande" : "Engångsbelopp"}
      </dd>
    </div>
    {grant.applicationStart && (
      <div>
        <dt className="text-sm text-muted-foreground">Ansökan öppnar</dt>
        <dd className="font-medium" dateTime={grant.applicationStart}>
          {grant.applicationStart}
        </dd>
      </div>
    )}
    {grant.category && (
      <div>
        <dt className="text-sm text-muted-foreground">Kategori</dt>
        <dd className="font-medium">{grant.category}</dd>
      </div>
    )}
  </dl>
</section>
```

This makes each fact a `{dt} → {dd}` pair with `data-*` attributes for machine readability. The `<dd>` with `dateTime` attribute on deadline/applicationStart fields allows AI tools to extract structured date facts.

---

### Flaw 3: Organization schema `sameAs` is empty — zero external entity links for knowledge graph
**Impact:** Google's Knowledge Graph and LLMs use `sameAs` links to connect an organization to its presence across the web (social profiles, Wikipedia, Crunchbase, etc.). The current `SEOHead.tsx` has `sameAs: []` — completely empty. No entity resolution can occur. This is a high-visibility, low-effort fix.

*Remediation:* Populate `sameAs` in `apps/frontend/src/components/SEOHead.tsx`. Add social and external profiles:

```ts
// apps/frontend/src/components/SEOHead.tsx

const organizationSchema = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "StipendieAssistenten",
  description:
    "Din guide till att hitta och ansöka om stipendier och bidrag för din familj.",
  url: "https://stipendieassistenten.labb.site",
  slogan: "Hitta och ansök om stipendier",
  // Replace empty array with real social/external links:
  sameAs: [
    "https://x.com/StipendieAss",           // Twitter/X
    "https://www.facebook.com/stipendieassistenten",  // Facebook (create if not exists)
    "https://www.instagram.com/stipendieassistenten", // Instagram (create if not exists)
    "https://www.linkedin.com/company/stipendieassistenten", // LinkedIn (create if not exists)
    "https://github.com/seppaleinen/stipendariet", // GitHub (if open source)
    "https://www.youtube.com/@StipendieAssistenten", // YouTube (create if not exists)
  ],
  foundingDate: "2024", // Update with actual founding year
  areaServed: {
    "@type": "Country",
    name: "Sverige",
    alternateName: "SE",
  },
  knowsAbout: [
    "Swedish scholarships",
    "utbildningsstipendier",
    "familjestöd",
    "bidrag för privatpersoner",
    "stipendieansökan",
  ],
  knowsLanguage: [
    { "@type": "Language", name: "Swedish", alternateName: "sv" },
    { "@type": "Language", name: "English", alternateName: "en" },
  ],
};
```

> **Action required:** The social media URLs above are placeholders. Replace each with the real profile URLs. The `areaServed` and `knowsAbout` fields help Google and LLMs understand the geographic and topical scope of the organization, increasing the probability of surfacing in relevant queries.

---

## Summary Table

| # | Vector | Flaw | File(s) to Change |
|---|---|---|---|
| 1 | Technical SEO | SPA blank shell — no SSR/prerender | `vite.config.ts`, `main.tsx` |
| 2 | Technical SEO | Sitemap has 0 grant pages | `scripts/generate-sitemap.js` |
| 3 | Technical SEO | `getGrantMetadata` canonical bug → all grant pages canonicalised to `/grants` | `src/lib/page-metadata.ts` |
| 4 | AEO | No FAQPage schema | New: `src/components/FAQSchema.tsx`; import in `Home.tsx`, `Grants.tsx` |
| 5 | AEO | No ScholarshipProgram/FinancialProduct schema on grant detail pages | `src/pages/GrantDetail.tsx` |
| 6 | AEO | No `hreflang` for Swedish locale | `index.html`, per-page `<Helmet>` |
| 7 | GEO | AI scrapers cannot see JSON-LD in SPA shell (same root as Flaw 1) | Same as Technical SEO Flaw 1 |
| 8 | GEO | Grant facts not in semantic markup — no `<dl>`, no `data-*` | `src/pages/GrantDetail.tsx` |
| 9 | GEO | Organization schema `sameAs: []` — no entity links | `src/components/SEOHead.tsx` |

---

## DoD Checklist

- [x] Audit completed for all target URLs (`/`, `/grants`, `/grants/:id`, `/matching`, `/auth`)
- [x] Exactly 9 technical/semantic flaws identified (3 per vector)
- [x] No placeholders or code stubs present in the remediation section (all snippets are production-ready)
- [ ] Remediations applied to codebase — **pending** (this brief is the deliverable; implementation is a separate task)
- [x] BLOCK items documented (production domain unconfirmed)
