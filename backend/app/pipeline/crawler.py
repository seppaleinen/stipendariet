import logging
import re
from typing import List, Dict
from playwright.async_api import async_playwright
from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_PATHS = re.compile(r'/(kontakt|ans[oö]kan|bidrag|stipendi(um|er))', re.IGNORECASE)
EXCLUDED_EXT = re.compile(r'\.(jpg|png|gif|pdf|doc|docx)$', re.IGNORECASE)

async def crawl_foundation_site(start_url: str) -> List[Dict[str, str]]:
    """
    Crawls the start_url (homepage) and internal links up to max_depth.
    Returns a list of dicts: [{"url": str, "content": str, "type": str}]
    """
    pages = []
    
    browserless_url = getattr(settings, 'BROWSERLESS_WS_URL', 'ws://browserless:3000') 
    
    try:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.connect_over_cdp(browserless_url)
            except Exception as e:
                logger.warning(f"Failed CDP connect, using fallback: {e}")
                browser = await p.chromium.launch(headless=True)
                
            page = await browser.new_page()
            
            logger.info(f"Crawling homepage: {start_url}")
            try:
                await page.goto(start_url, wait_until="domcontentloaded", timeout=30000)
                content_home = await page.evaluate("document.body.innerText")
                pages.append({"url": start_url, "content": content_home, "type": "homepage"})
            except Exception as e:
                logger.error(f"Error accessing homepage {start_url}: {e}")
                await browser.close()
                return pages
                
            try:
                links = await page.evaluate("""() => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)""")
                
                target_links = set()
                for link in links:
                    if link.startswith(start_url) or link.startswith('/'):
                        if ALLOWED_PATHS.search(link) and not EXCLUDED_EXT.search(link):
                            if link.startswith('/'):
                                link = start_url.rstrip('/') + link
                            target_links.add(link)
                            
                target_links = list(target_links)[:5]
                
                for link in target_links:
                    logger.info(f"Crawling subpage: {link}")
                    try:
                        await page.goto(link, wait_until="domcontentloaded", timeout=20000)
                        text_content = await page.evaluate("document.body.innerText")
                        pages.append({"url": link, "content": text_content, "type": "subpage"})
                    except Exception as e:
                        logger.error(f"Error crawling {link}: {e}")
            except Exception as e:
                logger.error(f"Error finding links on {start_url}: {e}")
                
            await browser.close()
    except Exception as e:
        logger.error(f"Playwright failure: {e}")
        
    return pages
