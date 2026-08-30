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

// Public routes that should be indexed
const staticRoutes = [
  { path: "/", changefreq: "daily", priority: "1.0" },
  { path: "/grants", changefreq: "weekly", priority: "0.9" },
  { path: "/matching", changefreq: "weekly", priority: "0.8" },
];

async function generateSitemap() {
  let grantCount = 0;

  // Fetch all published grant IDs from the backend at build time.
  // Falls back gracefully if the API is unreachable (log warning, skip grant URLs).
  let grantEntries = "";
  try {
    const res = await fetch(`${API_BASE}/grants?limit=1000&skip=0`);
    if (res.ok) {
      const { grants } = await res.json();
      grantCount = grants.length;
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
    console.warn("Could not fetch grants for sitemap:", err.message);
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

  let existing;
  try {
    existing = readFileSync(sitemapPath, "utf8");
  } catch {
    // File doesn't exist yet — proceed to write it.
  }

  if (existing === sitemap) {
    console.log(`Sitemap unchanged, skipping write: ${sitemapPath}`);
    console.log(`   Static routes indexed: ${staticRoutes.length}`);
    if (grantCount > 0) {
      console.log(`   Grant pages indexed: ${grantCount}`);
    }
    return;
  }

  writeFileSync(sitemapPath, sitemap);
  console.log(`Sitemap generated at ${sitemapPath}`);
  console.log(`   Static routes indexed: ${staticRoutes.length}`);
  if (grantCount > 0) {
    console.log(`   Grant pages indexed: ${grantCount}`);
  }
}

generateSitemap().catch(console.error);
