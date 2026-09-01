#!/usr/bin/env node
/**
 * Generate sitemap.xml — includes static routes + all pre-rendered grant pages.
 * Run: node scripts/generate-sitemap.js  (called automatically during `pnpm run build`)
 *
 * Source of truth for grant URLs: apps/frontend/dist/grants/<id>/index.html
 * (populated by scripts/prerender.js). Falls back to the public/ directory if
 * the build hasn't run yet (e.g. running the script standalone).
 *
 * lastmod data: fetched from the backend's lightweight /grants/sitemap-data endpoint.
 * Falls back to today's date if the backend is unreachable.
 *
 * image:image extension: added for every grant URL to improve Google Images SEO.
 */

import { readdirSync, readFileSync, writeFileSync, existsSync } from "fs";
import { join } from "path";

const SITE_URL = process.env.VITE_SITE_URL || "https://stipendieassistenten.labb.site";
const FRONTEND_DIR = join(import.meta.dirname, "..");
const DIST_GRANTS_DIR = join(FRONTEND_DIR, "dist", "grants");
const PUBLIC_DIR = join(FRONTEND_DIR, "public");
const FALLBACK_API = process.env.VITE_API_URL || "https://stipendieassistenten.labb.site/api";

// Public routes that should be indexed
const staticRoutes = [
  { path: "/", changefreq: "daily", priority: "1.0" },
  { path: "/grants", changefreq: "weekly", priority: "0.9" },
  { path: "/matching", changefreq: "weekly", priority: "0.8" },
];

/** Today's date as YYYY-MM-DD — used for static routes and fallback lastmod. */
const TODAY = new Date().toISOString().split("T")[0];

/**
 * Fetch {id → last_updated} map from the backend's lightweight sitemap-data endpoint.
 * Returns an empty Map if the backend is unreachable.
 */
async function fetchSitemapData() {
  try {
    const res = await fetch(`${FALLBACK_API}/grants/sitemap-data`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return new Map(data.map((item) => [item.id, item.last_updated]));
  } catch (err) {
    console.warn(`[generate-sitemap] Could not fetch /grants/sitemap-data: ${err.message}`);
    console.warn("[generate-sitemap] Falling back to today's date for all grant lastmod values.");
    return new Map();
  }
}

/**
 * Collect grant IDs from the local dist/grants/ directory.
 * Each subdirectory of dist/grants/ that contains an index.html is a pre-rendered
 * grant page and gets a sitemap entry.
 *
 * @returns {{ ids: string[], source: "dist" | "api" | "none" }}
 */
async function collectGrantIds() {
  // Primary: read from dist/grants/ (populated by prerender.js)
  if (existsSync(DIST_GRANTS_DIR)) {
    const entries = readdirSync(DIST_GRANTS_DIR, { withFileTypes: true });
    const ids = entries
      .filter((e) => e.isDirectory() && existsSync(join(DIST_GRANTS_DIR, e.name, "index.html")))
      .map((e) => e.name)
      .sort();
    if (ids.length > 0) {
      return { ids, source: "dist" };
    }
  }

  // Fallback: fetch from the API at build time (pre-prerender era).
  // This path only fires if dist/grants/ is missing or empty — i.e. someone ran
  // generate-sitemap.js without running prerender.js first.
  try {
    const res = await fetch(`${FALLBACK_API}/grants?limit=1000&skip=0`);
    if (res.ok) {
      const { grants } = await res.json();
      return { ids: grants.map((g) => g.id), source: "api" };
    }
  } catch (err) {
    console.warn("Could not fetch grants for sitemap:", err.message);
  }

  return { ids: [], source: "none" };
}

/**
 * Return the lastmod value for a given grant id.
 * Prefers the backend's last_updated; falls back to today's date.
 *
 * @param {string} id  — e.g. "foundation-1000203"
 * @param {Map<string, string|null>} lastUpdatedMap
 * @returns {string}  ISO date string YYYY-MM-DD
 */
function getLastmod(id, lastUpdatedMap) {
  const lu = lastUpdatedMap.get(id);
  if (lu) return lu.split("T")[0];
  return TODAY;
}

async function generateSitemap() {
  const [lastUpdatedMap, { ids: grantIds, source }] = await Promise.all([
    fetchSitemapData(),
    collectGrantIds(),
  ]);

  const hasLiveLastmod = lastUpdatedMap.size > 0;
  let liveCount = 0;
  let fallbackCount = 0;

  const grantEntries = grantIds
    .map((id) => {
      const lm = getLastmod(id, lastUpdatedMap);
      if (lm === TODAY && hasLiveLastmod) fallbackCount++;
      else liveCount++;

      return `
    <url>
      <loc>${SITE_URL}/grants/${id}</loc>
      <lastmod>${lm}</lastmod>
      <changefreq>weekly</changefreq>
      <priority>0.7</priority>
      <image:image>
        <image:loc>https://stipendieassistenten.labb.site/og-image.png</image:loc>
        <image:title>StipendieAssistenten</image:title>
        <image:caption>Utforska stipendiet och hitta det som passar dig bäst.</image:caption>
      </image:image>
    </url>`;
    })
    .join("");

  const staticEntries = staticRoutes
    .map(
      ({ path, changefreq, priority }) => `
    <url>
      <loc>${SITE_URL}${path}</loc>
      <lastmod>${TODAY}</lastmod>
      <changefreq>${changefreq}</changefreq>
      <priority>${priority}</priority>
    </url>`,
    )
    .join("");

  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
${staticEntries}${grantEntries}
</urlset>`;

  const sitemapPath = join(PUBLIC_DIR, "sitemap.xml");

  let existing;
  try {
    existing = readFileSync(sitemapPath, "utf8");
  } catch {
    // File doesn't exist yet — proceed to write it.
  }

  if (existing === sitemap) {
    console.log(`Sitemap unchanged, skipping write: ${sitemapPath}`);
    console.log(`   Static routes indexed: ${staticRoutes.length}`);
    if (grantIds.length > 0) {
      console.log(`   Grant pages indexed: ${grantIds.length} (source: ${source})`);
    }
    return;
  }

  writeFileSync(sitemapPath, sitemap);
  console.log(`Sitemap generated at ${sitemapPath}`);
  console.log(`   Static routes indexed: ${staticRoutes.length}`);
  if (grantIds.length > 0) {
    const totalLive = hasLiveLastmod ? liveCount : 0;
    const totalFallback = hasLiveLastmod ? fallbackCount : grantIds.length;
    console.log(`   Grant pages indexed: ${grantIds.length} (source: ${source})`);
    if (hasLiveLastmod) {
      console.log(`   lastmod — from API: ${totalLive}, fallback (today): ${totalFallback}`);
    } else {
      console.log(`   lastmod — all fallback (today): ${totalFallback} (API unreachable)`);
    }
  }
}

generateSitemap().catch(console.error);
