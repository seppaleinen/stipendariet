import asyncio
import logging
import re
from urllib.parse import urlparse

import httpx
import trafilatura
from playwright.async_api import async_playwright

try:
    from bs4 import BeautifulSoup
except ImportError:
    # BeautifulSoup is optional - used for link extraction
    BeautifulSoup = None

from app.core.config import settings
from app.pipeline.base import PipelineContext, PipelineStage
from app.utils.content_dedup import compute_content_hash, deduplicate_pages

logger = logging.getLogger(__name__)

ALLOWED_PATHS = re.compile(r'/(kontakt|ans[oö]kan|bidrag|stipendi(um|er))', re.IGNORECASE)
EXCLUDED_EXT = re.compile(r'\.(jpg|png|gif|pdf|doc|docx)$', re.IGNORECASE)


async def _fetch_robots_txt(domain: str) -> set[str]:
    """Fetch robots.txt for domain once. Returns set of disallowed paths."""
    try:
        robots_url = f"{domain}/robots.txt"
        async with httpx.AsyncClient(
            headers={"User-Agent": settings.CRAWLER_USER_AGENT},
            timeout=settings.CRAWL_TIMEOUT,
            follow_redirects=True,
        ) as client:
            response = await client.get(robots_url)
            if response.status_code == 200:
                disallowed = set()
                for line in response.text.split("\n"):
                    line = line.strip()
                    if line.lower().startswith("disallow:"):
                        path = line.split(":", 1)[1].strip()
                        if path:
                            disallowed.add(path)
                return disallowed
    except Exception as e:
        logger.debug(f"Robots.txt fetch failed for {domain}: {e}")

    # Default to allow all if fetch fails or robots.txt not found
    return set()


def _is_allowed_by_robots(url: str, disallowed_paths: set[str]) -> bool:
    """Check if URL path is allowed against parsed robots.txt disallowed paths."""
    try:
        path = urlparse(url).path
        return not any(path.startswith(d) for d in disallowed_paths)
    except Exception as e:
        logger.debug(f"Robots.txt path check failed for {url}: {e}")
        return True


def crawl_with_trafilatura(url: str) -> dict | None:
    """
    Crawl using trafilatura (faster, no browser).

    Args:
        url: URL to crawl

    Returns:
        Dict with url, markdown, content_hash, source="trafilatura"
        or None if crawl fails or content too short.
        Note: "type" is NOT included — caller sets type based on context.
    """
    try:
        downloaded = trafilatura.fetch_url(url)

        if not downloaded:
            logger.warning(f"Trafilatura fetch failed for {url}: no download")
            return None

        markdown = trafilatura.extract(
            downloaded,
            output_format="markdown",
            include_comments=False,
            include_tables=False,
        )

        if not markdown or len(markdown.strip()) < settings.CRAWL_MIN_CONTENT_LENGTH:
            logger.debug(
                f"Trafilatura content too short for {url}: "
                f"{len(markdown or '')} chars"
            )
            return None

        content_hash = compute_content_hash(markdown)

        return {
            "url": url,
            "markdown": markdown,
            "content_hash": content_hash,
            "source": "trafilatura",
        }

    except Exception as e:
        logger.warning(f"Trafilatura crawl failed for {url}: {e}")
        return None


async def _crawl_with_playwright(url: str, is_homepage: bool = False) -> dict | None:
    """Fallback crawl using Playwright (JS-heavy sites)."""
    browserless_url = getattr(settings, 'BROWSERLESS_WS_URL', None)

    try:
        async with async_playwright() as p:
            try:
                if browserless_url:
                    browser = await p.chromium.connect_over_cdp(browserless_url)
                else:
                    browser = await p.chromium.launch(headless=True)
            except Exception as e:
                logger.warning(f"Playwright launch failed, using local chromium: {e}")
                browser = await p.chromium.launch(headless=True)

            page = await browser.new_page(
                user_agent=settings.CRAWLER_USER_AGENT
            )

            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=settings.CRAWL_TIMEOUT * 1000,
                )
                markdown = await page.evaluate("document.body.innerText")
                await browser.close()

                if not markdown or len(markdown.strip()) < settings.CRAWL_MIN_CONTENT_LENGTH:
                    logger.debug(
                        f"Playwright content too short for {url}: "
                        f"{len(markdown or '')} chars"
                    )
                    return None

                content_hash = compute_content_hash(markdown)

                return {
                    "url": url,
                    "markdown": markdown,
                    "content_hash": content_hash,
                    "source": "playwright",
                }

            except Exception as e:
                await browser.close()
                logger.error(f"Playwright crawl failed for {url}: {e}")
                return None

    except Exception as e:
        logger.error(f"Playwright failure: {e}")
        return None


async def crawl_foundation_site(start_url: str) -> list[dict[str, str]]:
    """
    Crawls the start_url (homepage) and internal links.
    Tries trafilatura first, falls back to Playwright for JS-heavy sites.
    Returns a list of dicts: [{"url": str, "markdown": str, "type": str, "content_hash": str, "source": str}]
    """
    pages = []
    crawled_urls = set()

    # Fetch robots.txt once for this domain
    parsed_start = urlparse(start_url)
    domain = f"{parsed_start.scheme}://{parsed_start.netloc}"
    disallowed_paths = await _fetch_robots_txt(domain)

    # Check robots.txt for homepage
    if not _is_allowed_by_robots(start_url, disallowed_paths):
        logger.warning(f"Robots.txt disallows crawling {start_url}")
        return pages

    # Fetch homepage HTML once for both content and link extraction
    try:
        logger.info(f"Crawling homepage: {start_url}")
        # Blocking network call - run in thread pool
        downloaded = await asyncio.to_thread(
            trafilatura.fetch_url,
            start_url,
        )

        if downloaded:
            # Extract markdown from the same download
            markdown = trafilatura.extract(
                downloaded,
                output_format="markdown",
                include_comments=False,
                include_tables=False,
            )

            if markdown and len(markdown.strip()) >= settings.CRAWL_MIN_CONTENT_LENGTH:
                content_hash = compute_content_hash(markdown)
                page_result = {
                    "url": start_url,
                    "markdown": markdown,
                    "type": "homepage",
                    "content_hash": content_hash,
                    "source": "trafilatura",
                }
                pages.append(page_result)
                crawled_urls.add(start_url)
                await asyncio.sleep(settings.CRAWL_POLITE_DELAY)

                # Extract links from the SAME downloaded HTML
                if BeautifulSoup:
                    soup = BeautifulSoup(downloaded, 'html.parser')
                    links = []
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if href.startswith(start_url) or href.startswith('/'):
                            if ALLOWED_PATHS.search(href) and not EXCLUDED_EXT.search(href):
                                if href.startswith('/'):
                                    href = start_url.rstrip('/') + href
                                if href not in crawled_urls:
                                    links.append(href)

                    # Limit subpages
                    target_links = links[:settings.CRAWL_MAX_SUBPAGES]

                    for link in target_links:
                        # Check robots.txt
                        if not _is_allowed_by_robots(link, disallowed_paths):
                            logger.debug(f"Robots.txt disallows {link}")
                            continue

                        logger.info(f"Crawling subpage: {link}")
                        # Blocking network call - run in thread pool
                        page_result = await asyncio.to_thread(crawl_with_trafilatura, link)

                        if not page_result:
                            # Fallback to Playwright
                            logger.info(f"Trafilatura failed for {link}, trying Playwright")
                            page_result = await _crawl_with_playwright(link, is_homepage=False)

                        if page_result:
                            page_result["type"] = "subpage"
                            pages.append(page_result)
                            crawled_urls.add(link)

                        # Polite delay
                        await asyncio.sleep(settings.CRAWL_POLITE_DELAY)
            else:
                # Content too short, fallback to Playwright
                logger.info(f"Trafilatura content too short for homepage {start_url}, trying Playwright")
                page_result = await _crawl_with_playwright(start_url, is_homepage=True)
                if page_result:
                    page_result["type"] = "homepage"
                    pages.append(page_result)
                    crawled_urls.add(start_url)
                    await asyncio.sleep(settings.CRAWL_POLITE_DELAY)
        else:
            # Download failed, fallback to Playwright
            logger.info(f"Trafilatura fetch failed for homepage {start_url}, trying Playwright")
            page_result = await _crawl_with_playwright(start_url, is_homepage=True)
            if page_result:
                page_result["type"] = "homepage"
                pages.append(page_result)
                crawled_urls.add(start_url)
                await asyncio.sleep(settings.CRAWL_POLITE_DELAY)

    except Exception as e:
        logger.error(f"Error finding links on {start_url}: {e}")

    # Deduplicate pages
    pages = deduplicate_pages(pages)

    return pages


class CrawlStage(PipelineStage):
    """Pipeline stage for crawling foundation sites."""
    name = "crawl"

    async def run(self, ctx: PipelineContext) -> None:
        if not ctx.active_source:
            return

        url = ctx.active_source.get("url")
        if not url:
            return

        pages = await crawl_foundation_site(url)
        ctx.crawled_pages = pages
