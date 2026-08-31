#!/usr/bin/env node
/**
 * Prerender script — generates static HTML files for static-shell routes
 * (Home, /grants listing, /matching, /auth). Individual /grants/:id pages
 * are rendered on-demand by scripts/ssr-server.js — see GitHub issue #2.
 *
 * Run automatically after `vite build` via `pnpm run build`.
 *   Full build:  vite build && node scripts/prerender.js && node scripts/generate-sitemap.js
 *   Or standalone (NOT recommended): node scripts/prerender.js
 *
 * IMPORTANT: This script reads the HTML template from `dist/index.html` (the
 * Vite build output), NOT the source `index.html`.  The build output contains
 * the correct hashed asset links (<link rel="stylesheet" href="/assets/index-*.css">
 * and <script type="module" src="/assets/index-*.js">).  If you run this script
 * without a prior `vite build`, it falls back to the source template with a
 * loud warning — the resulting pages will reference `/src/entry-client.tsx` and
 * have no CSS, which is NOT suitable for deployment.
 *
 * Env vars (set in .env or CI pipeline):
 *   VITE_SITE_URL  — public site URL (default: https://stipendieassistenten.labb.site)
 *   VITE_API_URL   — backend API base (default: https://stipendieassistenten.labb.site/api)
 *
 * Note: Per-grant prerendering was removed in issue #2. Previously this script
 * generated up to 500 static /grants/<id> files (~88 API pages + 500 detail
 * fetches) — a ~10 min build step that left ~96% of grant detail URLs as SPA
 * shells. Now only static-shell routes are built; the SSR fallback server
 * (scripts/ssr-server.js) renders the rest on demand with 1h cache TTL.
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
// Individual /grants/:id pages are NOT in this list — they're served by
// scripts/ssr-server.js on demand. Only "shell" routes that benefit from being
// pre-rendered go here.

const STATIC_ROUTES = [
  { url: "/", outDir: "" },
  { url: "/grants", outDir: "grants" },
  { url: "/matching", outDir: "matching" },
  { url: "/auth", outDir: "auth" },
];

// ── API helpers ─────────────────────────────────────────────────────────────

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

// ── Main ────────────────────────────────────────────────────────────────────

let templateHtml = "";

async function main() {
  console.log("\n🔨  Prerendering static-shell routes...\n");
  console.log(`   Site: ${SITE_URL}`);
  console.log(`   API:  ${API_BASE}`);
  console.log(`   Note: /grants/:id pages are rendered on-demand by ssr-server.js\n`);

  // Load the HTML template from the Vite build output (dist/index.html),
  // which contains the correct hashed asset links (CSS, JS modules).
  // Falling back to the source template will produce broken pages — warn loudly.
  const builtTemplatePath = join(DIST, "index.html");
  if (existsSync(builtTemplatePath)) {
    templateHtml = readFileSync(builtTemplatePath, "utf8");
    console.log(`   Template: ${builtTemplatePath}`);
  } else {
    console.warn(
      "\n⚠️  WARNING: dist/index.html not found — no prior `vite build` detected.\n" +
      "   Falling back to source index.html. The output will reference\n" +
      "   /src/entry-client.tsx and contain NO CSS. Do NOT deploy these pages.\n" +
      "   Run:  vite build && node scripts/prerender.js\n"
    );
    templateHtml = readFileSync(join(ROOT, "index.html"), "utf8");
  }

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

  // ── Summary ────────────────────────────────────────────────────────────
  console.log(`\n✅  Prerendering complete.  ${ok} OK, ${fail} failed.`);
  console.log(`   /grants/:id pages are served on-demand by ssr-server.js (1h cache).\n`);
}

main().catch((err) => {
  console.error("Fatal prerender error:", err);
  process.exit(1);
});