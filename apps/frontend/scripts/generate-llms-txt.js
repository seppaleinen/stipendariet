#!/usr/bin/env node
/**
 * Generate llms.txt — machine-readable grant export for AI platform ingestion.
 * Run: node scripts/generate-llms-txt.js  (called automatically during `pnpm run build`)
 *
 * Fetches all grants from GET /api/grants/export.json (with paginated fallback).
 * Writes apps/frontend/public/llms.txt — one grant per line, pipe-delimited.
 * If API is unreachable, warn and skip (don't fail the build).
 */

import { writeFileSync } from "fs";
import { join } from "path";

const SITE_URL = process.env.VITE_SITE_URL || "https://stipendieassistenten.labb.site";
const FRONTEND_DIR = join(import.meta.dirname, "..");
const PUBLIC_DIR = join(FRONTEND_DIR, "public");
const FALLBACK_API = process.env.VITE_API_URL || "https://stipendieassistenten.labb.site/api";

const DESCRIPTION_MAX = 500;

/**
 * Truncate description to max length with ellipsis.
 * @param {string|null|undefined} text
 * @param {number} max
 * @returns {string}
 */
function truncate(text, max = DESCRIPTION_MAX) {
  if (!text) return "";
  if (text.length <= max) return text;
  return text.slice(0, max).trimEnd() + "…";
}

/**
 * Fallback chain: enrichedDescription → summary → purpose (truncated)
 */
function getDescription(grant) {
  return (
    truncate(grant.enriched_description) ||
    truncate(grant.summary) ||
    truncate(grant.purpose) ||
    ""
  );
}

/**
 * Format amount string. Grant records from export.json may not have an amount
 * field — use Swedish fallback.
 */
function formatAmount(grant) {
  return grant.amount || "Belopp ej angivet";
}

/**
 * Format deadline string in Swedish.
 */
function formatDeadline(grant) {
  return grant.application_deadline || "Öppen";
}

/**
 * Format website URL — use grant.website_url or construct from SITE_URL.
 */
function getWebsiteUrl(grant) {
  return grant.website_url || `${SITE_URL}/grants/${grant.id}`;
}

/**
 * Format one grant as a pipe-delimited line.
 */
function formatLine(grant) {
  const title = grant.name || "Namnlöst stipendium";
  const amount = formatAmount(grant);
  const deadline = formatDeadline(grant);
  const description = getDescription(grant);
  const url = getWebsiteUrl(grant);
  return `# ${title} | ${amount} | Deadline: ${deadline} | ${description} | Ansökningslänk: ${url}`;
}

/**
 * Fetch all grants from export.json with pagination fallback.
 * Tries GET /api/grants/export.json?skip=0&limit=10000 first.
 * Falls back to paginated /grants?limit=200&skip=N if export.json is unavailable.
 * @returns {Promise<Array>}
 */
async function fetchAllGrants() {
  // Try the dedicated export endpoint first
  try {
    const res = await fetch(`${FALLBACK_API}/grants/export.json?skip=0&limit=10000`);
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data)) {
        console.log(`[generate-llms-txt] Fetched ${data.length} grants from /export.json`);
        return data;
      }
    }
    console.warn(`[generate-llms-txt] /export.json returned non-array or non-OK (${res.status})`);
  } catch (err) {
    console.warn(`[generate-llms-txt] /export.json unavailable: ${err.message}`);
  }

  // Fallback: paginated /grants
  console.log("[generate-llms-txt] Falling back to paginated /grants endpoint");
  const all = [];
  let skip = 0;
  const pageSize = 200;
  while (true) {
    const res = await fetch(`${FALLBACK_API}/grants?limit=${pageSize}&skip=${skip}`);
    if (!res.ok) {
      console.warn(`[generate-llms-txt] Failed to fetch page at skip=${skip}: HTTP ${res.status}`);
      break;
    }
    const { grants, has_more } = await res.json();
    all.push(...grants);
    if (!has_more) break;
    skip += pageSize;
    if (skip >= 2000) {
      console.warn("[generate-llms-txt] Stopping pagination at 2000 grants");
      break;
    }
  }
  console.log(`[generate-llms-txt] Fetched ${all.length} grants from paginated endpoint`);
  return all;
}

async function generateLlmsTxt() {
  const today = new Date().toISOString().split("T")[0];
  const header = `# StipendieAssistenten — Grant Export\n# Updated: ${today}\n\n`;

  let grants;
  try {
    grants = await fetchAllGrants();
  } catch (err) {
    console.error(`[generate-llms-txt] Fatal error fetching grants: ${err.message}`);
    return; // Don't fail the build
  }

  if (!grants || grants.length === 0) {
    console.warn("[generate-llms-txt] No grants fetched — skipping write");
    return;
  }

  const lines = grants.map(formatLine);
  const content = header + lines.join("\n") + "\n";

  const outPath = join(PUBLIC_DIR, "llms.txt");
  writeFileSync(outPath, content, "utf8");
  console.log(`[generate-llms-txt] Written ${grants.length} grants to ${outPath}`);
}

generateLlmsTxt().catch((err) => {
  console.error(`[generate-llms-txt] Unhandled error: ${err.message}`);
  // Don't exit with non-zero — we don't want to fail the build
});
