#!/usr/bin/env node
/**
 * Generate sitemap.xml for StipendieAssistenten SPA
 * Run: node scripts/generate-sitemap.js
 */

import { readFileSync, writeFileSync } from "fs";
import { join } from "path";

const SITE_URL = "https://stipendieassistenten.labb.site";
const PUBLIC_DIR = join(import.meta.dirname, "..", "public");

// Public routes that should be indexed
const publicRoutes = [
  "/",
  "/grants",
  "/matching",
  "/grants/:id", // Grant detail pages (dynamic)
];

// Protected routes that should be noindexed (handled by robots.txt)
// These are NOT included in sitemap:
// /auth, /applications, /generate, /profile-setup, /family-setup

function generateSitemap() {
  // No <lastmod>: dates stamped at build time are fabricated (SEO-meaningless —
  // Google ignores inaccurate lastmod) and made every build dirty the working
  // tree with date churn (issue #18). lastmod is optional per sitemap 0.9 spec.

  const publicRouteEntries = publicRoutes
    .filter((r) => !r.includes(":")) // Exclude dynamic routes from static sitemap
    .map((route) => {
      const url = `${SITE_URL}${route}`;
      return `
    <url>
      <loc>${url}</loc>
      <changefreq>${route === "/" ? "daily" : "weekly"}</changefreq>
      <priority>${route === "/" ? "1.0" : "0.8"}</priority>
    </url>`;
    }).join("");

  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${publicRouteEntries}
</urlset>`;

  const sitemapPath = join(PUBLIC_DIR, "sitemap.xml");

  let existing;
  try {
    existing = readFileSync(sitemapPath, "utf8");
  } catch {
    // File doesn't exist yet — proceed to write it.
  }

  if (existing === sitemap) {
    console.log(`✅ Sitemap unchanged, skipping write: ${sitemapPath}`);
    console.log(`   Public routes indexed: ${publicRoutes.filter((r) => !r.includes(":")).length}`);
    return;
  }

  writeFileSync(sitemapPath, sitemap);
  console.log(`✅ Sitemap generated at ${sitemapPath}`);
  console.log(`   Public routes indexed: ${publicRoutes.filter((r) => !r.includes(":")).length}`);
}

generateSitemap();
