#!/usr/bin/env node
/**
 * Express SSR fallback server — bridges the static+prerendered build output
 * with on-demand server-side rendering for grant detail pages.
 *
 * Problem solved:
 *   Build-time prerendering is capped at 500 grants (~3% of ~17k total).
 *   All other /grants/<id> URLs fall back to the Vite SPA shell (index.html),
 *   which is an empty React SPA — crawlers see no content.
 *
 * How it works:
 *   1. Static files (dist/) are served directly (prerendered pages, assets, etc.)
 *   2. GET /grants/:id  →  check dist/grants/:id/index.html (static hit), else
 *                          fetch grant from backend API, render via SSR entry,
 *                          inject HTML into dist/index.html template, return.
 *   3. Rendered HTML is cached in dist/.ssr-cache for 1 hour.
 *   4. POST /cache/invalidate/grants/:id  →  purge cache entry (called by
 *      enrichment webhook after grant update).
 *
 * Uses Node's built-in `http` module — no Express dependency required.
 * The routing surface is tiny (3 routes + static fallback) and the spec
 * originally said "Express" only because that's the common idiom; this is
 * simpler and adds zero deps.
 *
 * Usage:
 *   node scripts/ssr-server.js
 *   PORT=3001 node scripts/ssr-server.js
 *   VITE_API_URL=https://api.example.com node scripts/ssr-server.js
 */

import { createServer } from "http";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import {
  readFileSync,
  existsSync,
  mkdirSync,
  writeFileSync,
  unlinkSync,
  statSync,
} from "fs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const DIST = join(ROOT, "dist");
const CACHE_DIR = join(DIST, ".ssr-cache");
const TEMPLATE_PATH = join(DIST, "index.html");
const SSR_PATH = join(DIST, "server", "entry-server.js");

const PORT = parseInt(process.env.PORT || "3001", 10);
const API_BASE = process.env.VITE_API_URL
  ? process.env.VITE_API_URL.replace(/\/$/, "")
  : "http://localhost:8000/api";
const CACHE_TTL_SECONDS = parseInt(process.env.SSR_CACHE_TTL || "3600", 10);

// ── Caching ──────────────────────────────────────────────────────────────────

function ensureCacheDir() {
  if (!existsSync(CACHE_DIR)) mkdirSync(CACHE_DIR, { recursive: true });
}

function cachePath(grantId) {
  return join(CACHE_DIR, `${grantId}.html`);
}

function readCache(grantId) {
  try {
    const filePath = cachePath(grantId);
    if (!existsSync(filePath)) return null;
    const { html, ts, ttl } = JSON.parse(readFileSync(filePath, "utf8"));
    if (Date.now() - ts > ttl * 1000) return null;
    return html;
  } catch {
    return null;
  }
}

function writeCache(grantId, html) {
  try {
    ensureCacheDir();
    writeFileSync(
      cachePath(grantId),
      JSON.stringify({ html, ts: Date.now(), ttl: CACHE_TTL_SECONDS }),
      "utf8"
    );
  } catch (err) {
    console.error(`[ssr-server] cache write failed for ${grantId}:`, err.message);
  }
}

function invalidateCache(grantId) {
  try {
    const filePath = cachePath(grantId);
    if (existsSync(filePath)) unlinkSync(filePath);
    console.log(`[ssr-server] cache invalidated: ${grantId}`);
  } catch (err) {
    console.error(`[ssr-server] cache invalidate failed for ${grantId}:`, err.message);
  }
}

// ── SSR module (lazy-load) ───────────────────────────────────────────────────

let ssrRender = null;

async function getSsrRender() {
  if (ssrRender) return ssrRender;
  if (!existsSync(SSR_PATH)) {
    throw new Error(
      `SSR bundle not found at ${SSR_PATH}. Run \`vite build\` first.`
    );
  }
  const mod = await import(SSR_PATH);
  ssrRender = mod.render;
  return ssrRender;
}

// ── Backend → frontend grant mapping ────────────────────────────────────────
// Mirrors mapGrantFromBackend() in src/lib/api.ts. Keeping it in sync ensures
// the SSR-rendered HTML uses the same field names the React components expect.

function formatDate(d) {
  if (!d) return undefined;
  try {
    return new Date(d).toISOString().split("T")[0];
  } catch {
    return undefined;
  }
}

function mapGrantFromBackend(grant) {
  const deadline = grant.deadline || grant.application_deadline;
  return {
    id: (grant.id ?? "").toString(),
    title: grant.name || grant.title || "Namn saknas",
    summary:
      grant.summary || grant.description || "Ingen sammanfattning tillgänglig",
    description:
      grant.description || grant.summary || "Ingen beskrivning tillgänglig",
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
    enrichedDescription: grant.enriched_description || undefined,
  };
}

// ── HTML template injection ──────────────────────────────────────────────────

function readTemplate() {
  if (existsSync(TEMPLATE_PATH)) {
    return readFileSync(TEMPLATE_PATH, "utf8");
  }
  throw new Error(
    `Template not found at ${TEMPLATE_PATH}. Run \`vite build\` first.`
  );
}

/**
 * Inject rendered HTML and serialized <head> content into the HTML template.
 * Uses the same regex-based approach as scripts/prerender.js for predictability.
 */
function injectHtmlIntoTemplate(templateHtml, { html, head }) {
  let result = templateHtml;
  if (head) {
    result = result.replace(/<\/head>/i, `\n${head}\n</head>`);
  }
  result = result.replace(
    /<div id="root">[\s\S]*?<\/div>/i,
    `<div id="root">${html}</div>`
  );
  return result;
}

// ── Tiny router ───────────────────────────────────────────────────────────────

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".txt": "text/plain",
  ".xml": "application/xml",
};

function mimeFor(filePath) {
  const idx = filePath.lastIndexOf(".");
  if (idx < 0) return "application/octet-stream";
  return MIME_TYPES[filePath.slice(idx).toLowerCase()] || "application/octet-stream";
}

/**
 * Try to serve a static file from DIST. Returns true if served, false if not found.
 */
function serveStatic(req, res, relativePath) {
  // Sanitize: no leading slash, no path traversal
  const safe = relativePath.replace(/^\/+/, "").replace(/\.\.+/g, "");
  if (!safe) return false;
  const filePath = join(DIST, safe);

  // Ensure filePath is actually inside DIST
  if (!filePath.startsWith(DIST)) return false;

  if (!existsSync(filePath)) return false;
  const stat = statSync(filePath);
  if (!stat.isFile()) return false;

  res.setHeader("Content-Type", mimeFor(filePath));
  if (/\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$/i.test(filePath)) {
    res.setHeader("Cache-Control", "public, max-age=31536000, immutable");
  }
  res.statusCode = 200;
  res.end(readFileSync(filePath));
  return true;
}

function sendJson(res, status, obj) {
  res.setHeader("Content-Type", "application/json");
  res.statusCode = status;
  res.end(JSON.stringify(obj));
}

function sendText(res, status, text, contentType = "text/plain") {
  res.setHeader("Content-Type", contentType);
  res.statusCode = status;
  res.end(text);
}

async function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk) => (data += chunk));
    req.on("end", () => resolve(data));
    req.on("error", reject);
  });
}

// ── Request handlers ──────────────────────────────────────────────────────────

async function handleGrantPage(req, res, grantId) {
  // 1. Try static prerendered page first
  const staticFile = join(DIST, "grants", grantId, "index.html");
  if (existsSync(staticFile)) {
    res.setHeader("X-SSR-Cache", "HIT");
    res.setHeader("Cache-Control", "public, max-age=3600");
    sendText(res, 200, readFileSync(staticFile, "utf8"), "text/html; charset=utf-8");
    return;
  }

  // 2. Check our file cache
  const cached = readCache(grantId);
  if (cached) {
    res.setHeader("X-SSR-Cache", "HIT");
    res.setHeader("Cache-Control", "public, max-age=3600");
    sendText(res, 200, cached, "text/html; charset=utf-8");
    return;
  }

  // 3. SSR: fetch from backend and render
  try {
    const apiUrl = `${API_BASE}/grants/${encodeURIComponent(grantId)}`;
    const ctrl = new AbortController();
    const timeoutId = setTimeout(() => ctrl.abort(), 10000);
    let apiRes;
    try {
      apiRes = await fetch(apiUrl, { signal: ctrl.signal });
    } finally {
      clearTimeout(timeoutId);
    }

    if (apiRes.status === 404) {
      sendJson(res, 404, { error: "Grant not found" });
      return;
    }
    if (!apiRes.ok) {
      throw new Error(`Backend API returned HTTP ${apiRes.status}`);
    }

    const grantData = await apiRes.json();
    const mappedGrant = mapGrantFromBackend(grantData);

    const render = await getSsrRender();
    const { html, head } = await render(`/grants/${grantId}`, {
      grant: mappedGrant,
    });

    const templateHtml = readTemplate();
    const pageHtml = injectHtmlIntoTemplate(templateHtml, { html, head });

    writeCache(grantId, pageHtml);

    res.setHeader("X-SSR-Cache", "MISS");
    res.setHeader("Cache-Control", "public, max-age=3600");
    sendText(res, 200, pageHtml, "text/html; charset=utf-8");
  } catch (err) {
    console.error(`[ssr-server] /grants/${grantId}:`, err.message);
    sendJson(res, 500, { error: "Internal server error" });
  }
}

// ── Server ────────────────────────────────────────────────────────────────────

const server = createServer(async (req, res) => {
  const url = req.url || "/";
  const method = req.method || "GET";

  try {
    // Health check
    if (method === "GET" && url === "/health") {
      sendText(res, 200, "ok");
      return;
    }

    // Cache invalidation
    {
      const m = url.match(/^\/cache\/invalidate\/grants\/([^/?#]+)/);
      if (method === "POST" && m) {
        invalidateCache(m[1]);
        sendJson(res, 200, { ok: true, id: m[1] });
        return;
      }
    }

    // Grant detail: GET /grants/:id
    {
      const m = url.match(/^\/grants\/([^/?#]+)\/?$/);
      if (method === "GET" && m) {
        await handleGrantPage(req, res, m[1]);
        return;
      }
    }

    // Static files: any other GET → serve from dist/
    if (method === "GET") {
      const pathname = url.split("?")[0].split("#")[0];
      if (serveStatic(req, res, pathname)) return;

      // SPA fallback: serve index.html for client-side routes
      const spaShell = join(DIST, "index.html");
      if (existsSync(spaShell)) {
        sendText(res, 200, readFileSync(spaShell, "utf8"), "text/html; charset=utf-8");
        return;
      }
      sendText(res, 404, "Not found");
      return;
    }

    sendText(res, 405, "Method not allowed");
  } catch (err) {
    console.error(`[ssr-server] unhandled error on ${method} ${url}:`, err);
    sendJson(res, 500, { error: "Internal server error" });
  }
});

// ── Startup ───────────────────────────────────────────────────────────────────

ensureCacheDir();

server.listen(PORT, () => {
  console.log(`SSR server listening on :${PORT}`);
  console.log(`  API base:    ${API_BASE}`);
  console.log(`  Cache dir:   ${CACHE_DIR}`);
  console.log(`  Cache TTL:   ${CACHE_TTL_SECONDS}s`);
});