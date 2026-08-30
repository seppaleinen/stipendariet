#!/usr/bin/env node
/**
 * Prerender script — generates static HTML files for public routes.
 *
 * Run automatically after `vite build` via `pnpm run build`.
 * Or standalone: node scripts/prerender.js
 *
 * Env vars (set in .env or CI pipeline):
 *   VITE_SITE_URL  — public site URL (default: https://stipendieassistenten.labb.site)
 *   VITE_API_URL   — backend API base (default: https://stipendieassistenten.labb.site/api)
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { build as viteBuild } from "vite";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const DIST = join(ROOT, "dist");

const SITE_URL = process.env.VITE_SITE_URL || "https://stipendieassistenten.labb.site";
const API_BASE = process.env.VITE_API_URL || "https://stipendieassistenten.labb.site/api";

// ── Static routes to pre-render ──────────────────────────────────────────────

const STATIC_ROUTES = [
  { url: "/", outDir: "" },
  { url: "/grants", outDir: "grants" },
  { url: "/matching", outDir: "matching" },
  { url: "/auth", outDir: "auth" },
];

// ── API helpers ─────────────────────────────────────────────────────────────

/**
 * Fetch all grant IDs+metadata for sitemap & grant-detail prerendering.
 *
 * The backend enforces a per-page limit of 200 grants, so we paginate.
 * Note: building prerendered HTML for ~17k grants is expensive (~88 API pages
 * + 17k detail fetches). For initial deployment we cap at PRERENDER_GRANT_LIMIT
 * (default 500 — covers the most visible grants, similar to a sitemap tier).
 * Sitemap already includes all grants (separate script); prerender covers a
 * useful subset. Raise the cap once build budget allows.
 */
async function fetchAllGrants() {
  const PRERENDER_GRANT_LIMIT = parseInt(process.env.PRERENDER_GRANT_LIMIT || "500", 10);
  const pageSize = 200; // backend enforces limit <= 200
  const allGrants = [];
  let skip = 0;
  for (let page = 0; page < 100; page++) {
    try {
      const res = await fetch(`${API_BASE}/grants?limit=${pageSize}&skip=${skip}`);
      if (!res.ok) {
        if (allGrants.length > 0) break;
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      const grants = data.grants || [];
      allGrants.push(...grants);
      if (!data.has_more || grants.length < pageSize) break;
      skip += grants.length;
      if (allGrants.length >= PRERENDER_GRANT_LIMIT) {
        allGrants.length = PRERENDER_GRANT_LIMIT;
        break;
      }
    } catch (err) {
      if (allGrants.length > 0) break;
      console.warn("⚠  Could not fetch grants:", err.message);
      return [];
    }
  }
  if (allGrants.length >= PRERENDER_GRANT_LIMIT) {
    console.log(`   Capped at PRERENDER_GRANT_LIMIT=${PRERENDER_GRANT_LIMIT} (set higher to prerender more)`);
  }
  return allGrants;
}

/** Fetch the full grant object for a single grant (used to seed QueryClient). */
async function fetchGrant(id) {
  try {
    const res = await fetch(`${API_BASE}/grants/${id}`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/** Fetch the first page of grants for the /grants listing page. */
async function fetchGrantsPage() {
  try {
    const res = await fetch(`${API_BASE}/grants?limit=50&skip=0`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

// ── SSR rendering ────────────────────────────────────────────────────────────

let ssrRender = null;

/** Lazily build the SSR bundle, then return the render function. */
async function getSsrRender() {
  if (ssrRender) return ssrRender;

  console.log("🔧  Building SSR bundle...");
  const SSR_OUT = join(DIST, "server");

  await viteBuild({
    root: ROOT,
    build: {
      ssr: true,
      outDir: SSR_OUT,
      rollupOptions: {
        input: join(ROOT, "src/entry-server.tsx"),
        output: {
          // Ensure the output file is predictable
          entryFileNames: "entry-server.js",
        },
      },
    },
  });

  const ssrPath = join(SSR_OUT, "entry-server.js");
  if (!existsSync(ssrPath)) {
    throw new Error(`SSR build did not produce expected file: ${ssrPath}`);
  }

  const mod = await import(ssrPath);
  ssrRender = mod.render;
  console.log("✅  SSR bundle ready\n");
  return ssrRender;
}

// ── Backend → frontend grant mapping ─────────────────────────────────────────
// Mirrors mapGrantFromBackend() in src/lib/api.ts so the prerendered HTML uses
// the same field names the React components expect.
function mapGrantFromBackend(grant) {
  const deadline = grant.deadline || grant.application_deadline;
  const formatDate = (d) => {
    if (!d) return undefined;
    try {
      return new Date(d).toISOString().split("T")[0];
    } catch {
      return undefined;
    }
  };
  return {
    id: grant.id?.toString() ?? "",
    title: grant.name || grant.title || "Namn saknas",
    summary: grant.summary || grant.description || "Ingen sammanfattning tillgänglig",
    description: grant.description || grant.summary || "Ingen beskrivning tillgänglig",
    provider: grant.organization || grant.provider || "Okänd utgivare",
    amount: grant.amount || undefined,
    deadline: formatDate(deadline),
    category: grant.category || "Diverse",
    tags: Array.isArray(grant.tags) ? grant.tags : [],
    isRecurring: grant.cadence
      ? String(grant.cadence).toLowerCase().includes("år")
      : false,
    websiteUrl: grant.link || grant.website_url || undefined,
    orgnr: grant.orgnr || undefined,
    purpose: grant.purpose || undefined,
    translatedPurpose: grant.translated_purpose || undefined,
    address: grant.address || undefined,
    postnr: grant.postnr || undefined,
    postort: grant.postort || undefined,
    coAddress: grant.co_address || undefined,
    phone: grant.phone || undefined,
    signature: grant.signature || undefined,
    roles: Array.isArray(grant.roles) ? grant.roles : undefined,
    applicationDeadline: grant.application_deadline || undefined,
    applicationStart: grant.application_start || undefined,
    applicationMethod: grant.application_method || undefined,
    contactEmail: grant.contact_email || undefined,
    contactPhone: grant.contact_phone || undefined,
    whoCanApply: grant.who_can_apply || undefined,
  };
}

// ── HTML template manipulation ───────────────────────────────────────────────

/**
 * Inject rendered HTML and serialized <head> content into the HTML template.
 * Uses regex for predictable template structure — no external parser needed.
 */
function injectHtmlIntoTemplate(templateHtml, { html, head }) {
  let result = templateHtml;

  // Inject head content before </head>
  if (head) {
    result = result.replace(
      /<\/head>/i,
      `\n${head}\n</head>`
    );
  }

  // Inject body HTML into <div id="root">
  // The template always has <div id="root"></div> (empty)
  result = result.replace(
    /<div id="root">[\s\S]*?<\/div>/i,
    `<div id="root">${html}</div>`
  );

  return result;
}

function writePageHtml(outDir, pageHtml, url) {
  const dir = outDir ? join(DIST, outDir) : DIST;
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  const filePath = join(dir, "index.html");
  writeFileSync(filePath, pageHtml, "utf8");
  return filePath;
}

// ── Route rendering ──────────────────────────────────────────────────────────

async function renderStaticRoute(route) {
  const render = await getSsrRender();
  const { html, head } = await render(route.url);
  const pageHtml = injectHtmlIntoTemplate(templateHtml, { html, head });
  const filePath = writePageHtml(route.outDir, pageHtml, route.url);
  console.log(`  ✓ ${route.url}  →  ${filePath}`);
}

async function renderGrantDetailPage(grant) {
  const id = String(grant.id ?? "");
  if (!id) return;

  const outDir = `grants/${id}`;
  const render = await getSsrRender();

  // Fetch full grant data
  const grantData = await fetchGrant(id);
  if (!grantData) {
    console.warn(`  ⚠  /grants/${id}: not found in API, skipping`);
    return;
  }

  // Map raw backend grant (snake_case) to frontend Grant interface (camelCase).
  // Mirrors mapGrantFromBackend() in src/lib/api.ts.
  const mappedGrant = {
    ...grantData,
    foundationId: grantData.foundation_id,
    scholarshipAmount: grantData.scholarship_amount,
    applicationUrl: grantData.application_url,
    applicationDeadline: grantData.application_deadline,
    educationLevel: grantData.education_level,
    residencyRequirement: grantData.residency_requirement,
    requiredDocuments: grantData.required_documents,
    createdAt: grantData.created_at,
    updatedAt: grantData.updated_at,
  };

  const { html, head } = await render(`/grants/${id}`, { grant: mappedGrant });
  const pageHtml = injectHtmlIntoTemplate(templateHtml, { html, head });
  const filePath = writePageHtml(outDir, pageHtml, `/grants/${id}`);
  console.log(`  ✓ /grants/${id}  →  ${filePath}`);
}

// ── Main ────────────────────────────────────────────────────────────────────

let templateHtml = "";

async function main() {
  console.log("\n🔨  Prerendering public pages...\n");
  console.log(`   Site: ${SITE_URL}`);
  console.log(`   API:  ${API_BASE}\n`);

  // Load the HTML template once
  templateHtml = readFileSync(join(ROOT, "index.html"), "utf8");

  // ── 1. Static routes ────────────────────────────────────────────────────
  console.log("📄  Static routes...\n");
  let ok = 0, fail = 0;

  for (const route of STATIC_ROUTES) {
    try {
      await renderStaticRoute(route);
      ok++;
    } catch (err) {
      console.error(`  ✗ ${route.url}: ${err.message}`);
      fail++;
    }
  }

  // ── 2. /grants listing page with seeded first page ────────────────────
  console.log("\n📄  /grants listing...\n");
  try {
    const grantsData = await fetchGrantsPage();
    if (grantsData) {
      const render = await getSsrRender();
      // Map raw backend grants to the frontend Grant interface so the
      // listing page renders correctly with the same transform getGrants() applies.
      const mapped = {
        ...grantsData,
        grants: grantsData.grants.map(mapGrantFromBackend),
      };
      const { html, head } = await render("/grants", { grants: mapped });
      const pageHtml = injectHtmlIntoTemplate(templateHtml, { html, head });
      const filePath = writePageHtml("grants", pageHtml, "/grants");
      console.log(`  ✓ /grants  (${mapped.grants.length} grants seeded)  →  ${filePath}`);
    } else {
      console.warn("  ⚠  Could not fetch grants data, /grants will render empty");
      await renderStaticRoute({ url: "/grants", outDir: "grants" });
    }
  } catch (err) {
    console.error(`  ✗ /grants: ${err.message}`);
    fail++;
  }

  // ── 3. Individual grant detail pages ───────────────────────────────────
  console.log("\n📄  Grant detail pages...\n");
  const grants = await fetchAllGrants();
  console.log(`   Found ${grants.length} grants to prerender`);

  if (grants.length === 0) {
    console.warn("⚠  No grants fetched — skipping individual grant pages.");
    console.warn("   Check VITE_API_URL and ensure the backend is reachable at build time.\n");
  } else {
    for (const grant of grants) {
      try {
        await renderGrantDetailPage(grant);
        ok++;
      } catch (err) {
        console.error(`  ✗ /grants/${grant.id}: ${err.message}`);
        fail++;
      }
    }
  }

  // ── Summary ────────────────────────────────────────────────────────────
  console.log(`\n✅  Prerendering complete.  ${ok} OK, ${fail} failed.\n`);
}

main().catch((err) => {
  console.error("Fatal prerender error:", err);
  process.exit(1);
});
