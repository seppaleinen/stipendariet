import asyncio
import hashlib
import json
import logging
import re
import time
from urllib.parse import urlparse

import redis.asyncio as redis_asyncio
from ddgs import DDGS

from app.core.config import settings
from app.pipeline.base import PipelineContext, PipelineStage
from app.services.searxng_client import SearXNGClient, SearXNGError

logger = logging.getLogger(__name__)

# Domains that are pure business registries with no grant info — post-filter only
EXCLUDED_DOMAINS = [
    'bolagsfakta.se', 'allabolag.se', 'hitta.se', 'dnb.com',
    'eniro.se', 'ratsit.se', 'merinfo.se', 'foretagsfakta.se',
    'proff.se', 'largestcompanies.se', 'wikipedia.org',
    'globalgrant.com', 'krafman.se',
]

# Cache TTL: 7 days (604800 seconds)
SEARXNG_CACHE_TTL = 604800

# Lazy Redis connection (shared across discovery calls)
_redis_pool: redis_asyncio.Redis | None = None


async def _get_redis() -> redis_asyncio.Redis | None:
    """Lazy Redis connection (shared across calls). Returns None if Redis is unavailable."""
    global _redis_pool
    if _redis_pool is None:
        try:
            _redis_pool = redis_asyncio.from_url(
                settings.REDIS_URL, decode_responses=True
            )
            # Verify connection
            await _redis_pool.ping()
            logger.debug("Redis connection established (lazy init)")
        except Exception as e:
            logger.warning(f"Redis unavailable for SearXNG caching: {e}")
            _redis_pool = None
    return _redis_pool


def _cache_key(query: str, engines: list[str] | None = None) -> str:
    """SHA256-based cache key for a SearXNG query."""
    payload = json.dumps(
        {"q": query, "engines": engines or []},
        sort_keys=True,
        ensure_ascii=False,
    )
    return "searxng:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _slug(name: str) -> str:
    """Convert a foundation name to a URL-friendly slug."""
    s = name.lower()
    s = re.sub(r'[åä]', 'a', s)
    s = re.sub(r'[ö]', 'o', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def _is_excluded(url: str) -> bool:
    return any(domain in url.lower() for domain in EXCLUDED_DOMAINS)


REQUIRED_FIELDS = [
    "contact_email",
    "contact_phone",
    "application_open",
    "application_deadline",
    "who_can_apply",
    "how_to_apply",
    "notes",
    "enriched_description",
]


def generate_targeted_query(field_name: str, foundation_name: str) -> str:
    """Generate a targeted search query for a specific missing field.

    Swedish-specific query templates per field type.
    Args:
        field_name: One of the REQUIRED_FIELDS
        foundation_name: Name of the foundation

    Returns:
        A Swedish search query string targeting the specific field
    """
    query_templates = {
        "contact_email": f'"{foundation_name}" kontakt e-post',
        "contact_phone": f'"{foundation_name}" telefon kontakt',
        "application_open": f'"{foundation_name}" ansökan öppnar',
        "application_deadline": f'"{foundation_name}" sista ansökningsdag',
        "who_can_apply": f'"{foundation_name}" vem kan söka',
        "how_to_apply": f'"{foundation_name}" hur ansöker',
        "notes": f'"{foundation_name}" bidrag information',
        "enriched_description": f'"{foundation_name}" stiftelse ändamål',
    }

    return query_templates.get(field_name, f'"{foundation_name}" {field_name}')


def _valid_url(url: str) -> bool:
    """Validate url has http(s) scheme and netloc."""
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def _ddgs_search(query: str, max_results: int = 10) -> list:
    with DDGS() as ddgs:
        return ddgs.text(query, max_results=max_results)


def _probe_url(url: str) -> bool:
    """HEAD-check whether a URL returns 200."""
    try:
        import requests
        r = requests.head(url, timeout=5, allow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0"})
        return r.status_code < 400
    except Exception:
        return False


async def _searxng_search(query: str, max_results: int = 10) -> list[dict]:
    """
    Search via SearXNG with Redis caching (7-day TTL).

    Returns list of dicts: url, title, snippet, engine (from SearXNG).
    Caches results keyed by query. Returns [] on failure (does not raise).
    """
    redis = await _get_redis()
    key = _cache_key(query)
    if redis is not None:
        try:
            cached = await redis.get(key)
            if cached:
                logger.info(f"SearXNG cache hit for query: {query}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache read failed for query '{query}': {e}")

    client = SearXNGClient()
    try:
        results = await client.search(query, max_results=max_results)
    except SearXNGError as e:
        logger.warning(f"SearXNG client error for query '{query}': {e}")
        return []
    except Exception as e:
        logger.warning(f"SearXNG unexpected error for query '{query}': {e}")
        return []

    if redis is not None and results:
        try:
            await redis.set(key, json.dumps(results, ensure_ascii=False), ex=SEARXNG_CACHE_TTL)
        except Exception as e:
            logger.warning(f"Redis cache write failed for query '{query}': {e}")

    return results


async def discover_candidate_urls(
    foundation_name: str, orgnr: str = "", max_urls: int = 7
) -> list[dict]:
    """
    Multi-strategy discovery of candidate URLs for a Swedish foundation.

    Strategy order:
      1. Direct stiftelsemedel.se slug probe (fastest, most reliable source)
      2. SearXNG multi-engine search (primary), 4 strategies:
         a. "{name} {orgnr} site:se"
         b. "{name} bidrag ansökan"
         c. "{name} stipendium"
         d. "{name} kontakt"
      3. DDG fallback if SearXNG fails or returns < 3 candidates
    """
    candidates: list = []
    seen_urls: set = set()

    def add(url: str, title: str = "", snippet: str = "", engine: str = "", strategy: str = "") -> bool:
        if not url or not _valid_url(url) or url in seen_urls or _is_excluded(url):
            return False
        seen_urls.add(url)
        candidates.append({
            "url": url,
            "title": title,
            "snippet": snippet,
            "engine": engine,
            "strategy": strategy,
        })
        return True

    # --- Strategy 1: Direct stiftelsemedel.se slug probe (unchanged) ---
    slug = _slug(foundation_name)
    direct_url = f"https://stiftelsemedel.se/{slug}/"
    try:
        logger.info(f"Probing direct stiftelsemedel.se URL: {direct_url}")
        exists = await asyncio.to_thread(_probe_url, direct_url)
        if exists:
            add(direct_url, f"{foundation_name} – Stiftelsemedel.se", "", engine="probe", strategy="stiftelsemedel_direct")
            logger.info(f"  ✓ Direct URL valid: {direct_url}")
        else:
            logger.info(f"  ✗ Direct URL returned error: {direct_url}")
    except Exception as e:
        logger.warning(f"Direct probe failed: {e}")

    # --- Strategy 2: SearXNG multi-engine search (primary) ---
    searxng_success = False
    searxng_strategies = [
        ("site_se", f'"{foundation_name}" {orgnr} site:se' if orgnr else f'"{foundation_name}" site:se'),
        ("bidrag_ansokan", f'"{foundation_name}" bidrag ansökan'),
        ("stipendium", f'"{foundation_name}" stipendium'),
        ("kontakt", f'"{foundation_name}" kontakt'),
    ]

    for strategy_name, query in searxng_strategies:
        if len(candidates) >= max_urls:
            break
        started = time.monotonic()
        try:
            logger.info(f"SearXNG search [{strategy_name}]: {query}")
            results = await _searxng_search(query, max_results=10)
            duration = time.monotonic() - started
            logger.info(f"  → {len(results)} results in {duration:.1f}s")
            for r in results:
                url = r.get("url", "")
                if add(url, r.get("title", ""), r.get("snippet", ""), engine=r.get("engine", "searxng"), strategy=strategy_name):
                    if len(candidates) >= max_urls:
                        break
            if results:
                searxng_success = True
        except Exception as e:
            logger.warning(f"SearXNG strategy '{strategy_name}' failed: {e}")

    logger.info(f"  → {len(candidates)} candidates after SearXNG")

    # --- Strategy 3: DDG fallback ---
    # Fallback if SearXNG didn't succeed or we have fewer than 3 candidates
    if not searxng_success or len(candidates) < 3:
        logger.info(f"Falling back to DDG (candidates {len(candidates)}/3)")

        # Targeted search with orgnr (or stiftelse)
        if len(candidates) < max_urls:
            query2 = f'"{foundation_name}"' + (f' {orgnr}' if orgnr else ' stiftelse')
            try:
                logger.info(f"DDG targeted search: {query2}")
                results = await asyncio.to_thread(_ddgs_search, query2, 10)
                for r in results:
                    url = r.get("href", "")
                    if add(url, r.get("title", ""), r.get("body", ""), engine="ddg", strategy="ddg_targeted"):
                        if len(candidates) >= max_urls:
                            break
                logger.info(f"  → {len(candidates)} candidates after targeted search")
            except Exception as e:
                logger.warning(f"DDG targeted search failed: {e}")

        # Broader search if still under threshold
        if len(candidates) < 3:
            query3 = f"{foundation_name} stiftelse ansökan bidrag"
            try:
                logger.info(f"DDG broad search: {query3}")
                results = await asyncio.to_thread(_ddgs_search, query3, 10)
                for r in results:
                    url = r.get("href", "")
                    if add(url, r.get("title", ""), r.get("body", ""), engine="ddg", strategy="ddg_broad"):
                        if len(candidates) >= max_urls:
                            break
                logger.info(f"  → {len(candidates)} candidates after broad search")
            except Exception as e:
                logger.warning(f"DDG broad search failed: {e}")
    else:
        logger.info("SearXNG provided sufficient candidates, skipping DDG fallback")

    logger.info(f"Discovery complete for '{foundation_name}': {len(candidates)} candidates")
    return candidates


class DiscoveryStage(PipelineStage):
    """Pipeline stage for discovering candidate URLs."""
    name = "discovery"

    async def run(self, ctx: PipelineContext) -> None:
        candidates = await discover_candidate_urls(
            ctx.foundation_name,
            ctx.foundation_orgnr or "",
        )
        ctx.candidate_urls = candidates
