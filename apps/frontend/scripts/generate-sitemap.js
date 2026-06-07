#!/usr/bin/env node
/**
 * Generate sitemap.xml for StipendieAssistenten SPA
 * Run: node scripts/generate-sitemap.js
 */

import { writeFileSync } from "fs";
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
  const now = new Date().toISOString().slice(0, 10);

  const publicRouteEntries = publicRoutes
    .filter((r) => !r.includes(":")) // Exclude dynamic routes from static sitemap
    .map((route) => {
      const url = `${SITE_URL}${route}`;
      return `
    <url>
      <loc>${url}</loc>
      <lastmod>${now}</lastmod>
      <changefreq>${route === "/" ? "daily" : "weekly"}</changefreq>
      <priority>${route === "/" ? "1.0" : "0.8"}</priority>
    </url>`;
    }).join("");

  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${publicRouteEntries}
</urlset>`;

  writeFileSync(join(PUBLIC_DIR, "sitemap.xml"), sitemap);
  console.log(`✅ Sitemap generated at ${join(PUBLIC_DIR, "sitemap.xml")}`);
  console.log(`   Public routes indexed: ${publicRoutes.filter((r) => !r.includes(":")).length}`);
}

generateSitemap();
