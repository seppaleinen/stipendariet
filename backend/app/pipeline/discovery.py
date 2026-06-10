import asyncio
import logging
import re

from ddgs import DDGS

logger = logging.getLogger(__name__)

# Domains that are pure business registries with no grant info — post-filter only
EXCLUDED_DOMAINS = [
    'bolagsfakta.se', 'allabolag.se', 'hitta.se', 'dnb.com',
    'eniro.se', 'ratsit.se', 'merinfo.se', 'foretagsfakta.se',
    'proff.se', 'largestcompanies.se', 'wikipedia.org',
    'globalgrant.com', 'krafman.se',
]


def _slug(name: str) -> str:
    """Convert a foundation name to a URL-friendly slug."""
    s = name.lower()
    s = re.sub(r'[åä]', 'a', s)
    s = re.sub(r'[ö]', 'o', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def _is_excluded(url: str) -> bool:
    return any(domain in url.lower() for domain in EXCLUDED_DOMAINS)


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


async def discover_candidate_urls(
    foundation_name: str, orgnr: str = "", max_urls: int = 7
) -> list[dict]:
    """
    Multi-strategy discovery of candidate URLs for a Swedish foundation.

    Strategy order:
      1. Direct stiftelsemedel.se slug probe (fastest, most reliable source)
      2. Targeted DDG search: name + orgnr (specific)
      3. Broader DDG search: name + 'stiftelse ansökan' (wider net)
    """
    candidates: list = []
    seen_urls: set = set()

    def add(url: str, title: str = "", snippet: str = "") -> bool:
        if url in seen_urls or _is_excluded(url):
            return False
        seen_urls.add(url)
        candidates.append({"url": url, "title": title, "snippet": snippet})
        return True

    # --- Strategy 1: Direct stiftelsemedel.se slug ---
    slug = _slug(foundation_name)
    direct_url = f"https://stiftelsemedel.se/{slug}/"
    try:
        logger.info(f"Probing direct stiftelsemedel.se URL: {direct_url}")
        exists = await asyncio.to_thread(_probe_url, direct_url)
        if exists:
            add(direct_url, f"{foundation_name} – Stiftelsemedel.se", "")
            logger.info(f"  ✓ Direct URL valid: {direct_url}")
        else:
            logger.info(f"  ✗ Direct URL returned error: {direct_url}")
    except Exception as e:
        logger.warning(f"Direct probe failed: {e}")

    # --- Strategy 2: Targeted search with orgnr ---
    if len(candidates) < max_urls:
        query2 = f'"{foundation_name}"' + (f' {orgnr}' if orgnr else ' stiftelse')
        try:
            logger.info(f"DDG targeted search: {query2}")
            results = await asyncio.to_thread(_ddgs_search, query2, 10)
            for r in results:
                url = r.get("href", "")
                if url and add(url, r.get("title", ""), r.get("body", "")):
                    if len(candidates) >= max_urls:
                        break
            logger.info(f"  → {len(candidates)} candidates after targeted search")
        except Exception as e:
            logger.warning(f"DDG targeted search failed: {e}")

    # --- Strategy 3: Broader search ---
    if len(candidates) < 3:
        query3 = f"{foundation_name} stiftelse ansökan bidrag"
        try:
            logger.info(f"DDG broad search: {query3}")
            results = await asyncio.to_thread(_ddgs_search, query3, 10)
            for r in results:
                url = r.get("href", "")
                if url and add(url, r.get("title", ""), r.get("body", "")):
                    if len(candidates) >= max_urls:
                        break
            logger.info(f"  → {len(candidates)} candidates after broad search")
        except Exception as e:
            logger.warning(f"DDG broad search failed: {e}")

    logger.info(f"Discovery complete for '{foundation_name}': {len(candidates)} candidates")
    return candidates
