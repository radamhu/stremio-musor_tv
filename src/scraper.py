"""Web scraper for musor.tv live movies."""
import asyncio
import os
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Any, Dict
from playwright.async_api import async_playwright, Browser, Page
from models import LiveMovieRaw


logger = logging.getLogger(__name__)

# Configuration
RATE_MS = int(os.getenv("SCRAPE_RATE_MS", "30000"))

# Target pages – adjust as needed if markup changes
PAGES = [
    "https://musor.tv/most/tvben",
    "https://musor.tv/filmek"
]


class MusorTvScraper:
    """Thread-safe scraper for musor.tv with proper state management."""
    
    def __init__(self, rate_limit_ms: int = RATE_MS):
        """Initialize scraper with rate limiting.
        
        Args:
            rate_limit_ms: Minimum milliseconds between fetches
        """
        self._rate_limit_ms = rate_limit_ms
        self._browser: Optional[Browser] = None
        self._playwright: Optional[Any] = None  # Playwright instance
        self._last_fetch_at: float = 0
        self._fetch_lock = asyncio.Lock()
        self._in_flight_task: Optional[asyncio.Task] = None
        
        # Status tracking for health monitoring
        self._last_success_at: Optional[float] = None
        self._last_error_at: Optional[float] = None
        self._last_error: Optional[str] = None
        self._total_error_count: int = 0
        self._consecutive_error_count: int = 0
        
    async def initialize(self) -> None:
        """Initialize the browser instance."""
        if self._browser is None:
            logger.info("Initializing Playwright browser...")
            pw = await async_playwright().start()
            self._playwright = pw
            
            # Optimized browser settings for limited resources (e.g., Render free tier)
            self._browser = await pw.chromium.launch(
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",  # Overcome limited /dev/shm space
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-breakpad",
                    "--disable-component-extensions-with-background-pages",
                    "--disable-features=TranslateUI,BlinkGenPropertyTrees",
                    "--disable-ipc-flooding-protection",
                    "--disable-renderer-backgrounding",
                    "--enable-features=NetworkService,NetworkServiceInProcess",
                    "--force-color-profile=srgb",
                    "--hide-scrollbars",
                    "--metrics-recording-only",
                    "--mute-audio",
                    "--no-first-run",
                    "--disable-sync",
                    "--disable-default-apps"
                ],
                headless=True,
                timeout=60000  # Increased timeout for slow environments
            )
            logger.info("Browser initialized successfully")
    
    async def cleanup(self) -> None:
        """Cleanup browser resources."""
        if self._browser:
            logger.info("Closing browser...")
            await self._browser.close()
            self._browser = None
        
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            
    async def fetch_live_movies(self, force: bool = False) -> List[LiveMovieRaw]:
        """Fetch live movie data from musor.tv with rate limiting and deduplication.
        
        Args:
            force: If True, bypass rate limiting and force a fresh fetch
            
        Returns:
            List of LiveMovieRaw objects
        """
        async with self._fetch_lock:
            now = asyncio.get_event_loop().time() * 1000
            
            # If there's an in-flight request and we're not forcing, reuse it
            if not force and self._in_flight_task and not self._in_flight_task.done():
                logger.debug("Reusing in-flight fetch request")
                return await self._in_flight_task
            
            # Check rate limit
            if not force and (now - self._last_fetch_at < self._rate_limit_ms):
                elapsed = now - self._last_fetch_at
                remaining = self._rate_limit_ms - elapsed
                logger.debug(f"Rate limit active, {remaining}ms remaining")
                # If we have a recent completed task, return its result
                if self._in_flight_task and self._in_flight_task.done():
                    return self._in_flight_task.result()
                # Otherwise we need to fetch but respect the rate limit
                await asyncio.sleep(remaining / 1000)
            
            # Create and execute fetch task
            self._in_flight_task = asyncio.create_task(self._fetch())
            try:
                result = await self._in_flight_task
                self._last_fetch_at = asyncio.get_event_loop().time() * 1000
                
                # Update success status
                self._last_success_at = asyncio.get_event_loop().time()
                self._consecutive_error_count = 0
                
                return result
            except Exception as e:
                # Update error status
                self._last_error_at = asyncio.get_event_loop().time()
                self._last_error = str(e)
                self._total_error_count += 1
                self._consecutive_error_count += 1
                
                logger.error(f"Fetch failed: {e}", exc_info=True)
                raise
    
    async def _fetch(self) -> List[LiveMovieRaw]:
        """Internal method to perform the actual scraping.
        
        Returns:
            List of deduplicated LiveMovieRaw objects
        """
        logger.info("Starting fetch_live_movies...")
        
        # Ensure browser is initialized
        await self.initialize()
        
        if not self._browser:
            raise RuntimeError("Browser not initialized")
        
        results: List[LiveMovieRaw] = []
        
        for url in PAGES:
            logger.info(f"Scraping {url}")
            page = await self._browser.new_page(user_agent=self._get_user_agent())
            
            # Set a longer default timeout for slow environments
            page.set_default_timeout(90000)  # 90 seconds
            
            try:
                # Retry logic for page navigation with exponential backoff
                max_retries = 3
                retry_delay = 2  # seconds
                last_error = None
                
                for attempt in range(max_retries):
                    try:
                        logger.info(f"Loading {url} (attempt {attempt + 1}/{max_retries})")
                        await page.goto(
                            url, 
                            wait_until="domcontentloaded",  # Faster than 'load' or 'networkidle'
                            timeout=90000  # 90 seconds for slow hosts
                        )
                        logger.info(f"Successfully loaded {url}")
                        break  # Success, exit retry loop
                    except Exception as e:
                        last_error = e
                        logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {url}: {e}")
                        
                        if attempt < max_retries - 1:  # Don't sleep on last attempt
                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                            logger.info(f"Retrying in {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                        else:
                            # All retries failed
                            logger.error(f"All {max_retries} attempts failed for {url}: {last_error}")
                            raise
                
                # Accept cookie if present
                await self._safe_click(page, 'button:has-text("Elfogadom"), button:has-text("Accept")')
                await asyncio.sleep(2)  # Wait for content to load after cookie acceptance
                
                # Find show event tables - these contain the TV program information
                cards = page.locator("table.showeventtable")
                count = await cards.count()
                logger.info(f"Found {count} show events on {url}")
                
                for i in range(count):
                    el = cards.nth(i)
                    
                    try:
                        # Title is in .showeventtitle a
                        title_elem = el.locator(".showeventtitle a").first
                        title = await title_elem.text_content()
                        title = self._cleanup(title)
                        if not title:
                            continue
                        
                        # Time is in .showeventtime with format "2025.10.18 22:30"
                        time_elem = el.locator(".showeventtime").first
                        time_text = await time_elem.text_content()
                        time_text = self._cleanup(time_text)
                        
                        # Channel is in the img alt text or the link
                        channel_elem = el.locator(".showeventchannel img").first
                        channel = await channel_elem.get_attribute("alt")
                        channel = self._cleanup(channel) if channel else ""
                        
                        # Category/description is in the td with itemprop="description"
                        desc_elem = el.locator('td[itemprop="description"]').first
                        category = await desc_elem.text_content() if await desc_elem.count() > 0 else ""
                        category = self._cleanup(category)
                        
                        # Image is in .showeventimg
                        img_elem = el.locator("img.showeventimg").first
                        img = await img_elem.get_attribute("src") if await img_elem.count() > 0 else None
                        
                        start_iso = self._infer_start_iso(time_text)
                        results.append(LiveMovieRaw(
                            title=title,
                            start_iso=start_iso,
                            channel=channel,
                            category=category,
                            poster=self._absolutize(img)
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to parse show event {i} on {url}: {e}")
                        continue
                    
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}", exc_info=True)
            finally:
                await page.close()
        
        logger.info(f"Total raw results before deduplication: {len(results)}")
        deduplicated = self._dedupe(results)
        logger.info(f"Total results after deduplication: {len(deduplicated)}")
        return deduplicated
    
    @staticmethod
    def _cleanup(s: Optional[str]) -> str:
        """Clean up whitespace in string."""
        if not s:
            return ""
        return re.sub(r"\s+", " ", s).strip()
    
    @staticmethod
    def _infer_start_iso(time_text: str) -> str:
        """Parse musor.tv datetime format with midnight boundary handling.
        
        Handles two formats:
        1. Full datetime: '2025.10.18 22:30' (always accurate)
        2. Time only: '01:30' (uses day boundary detection)
        
        For time-only formats, if the parsed time is more than 12 hours in the past,
        we assume it refers to the next day (handles late-night programs).
        """
        # Try full datetime format first: YYYY.MM.DD HH:MM
        match = re.search(r"(\d{4})\.(\d{2})\.(\d{2})\s+(\d{1,2}):(\d{2})", time_text)
        if match:
            year, month, day, hour, minute = match.groups()
            d = datetime(int(year), int(month), int(day), int(hour), int(minute))
            return d.isoformat()
        
        # Fallback: HH:MM only - detect day boundary
        match = re.search(r"(\d{1,2}):(\d{2})", time_text)
        now = datetime.now()
        
        if match:
            hour, minute = int(match.group(1)), int(match.group(2))
            d = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If the time is significantly in the past (> 12 hours), assume next day
            # This handles late-night programs (e.g., scraping at 23:00, program at 01:00)
            time_diff = (d - now).total_seconds()
            if time_diff < -12 * 3600:  # More than 12 hours in the past
                d = d + timedelta(days=1)
                logger.debug(f"Adjusted date for time '{time_text}': crossed midnight boundary (now={now.strftime('%H:%M')}, parsed={hour:02d}:{minute:02d})")
            
            return d.isoformat()
        
        # No time pattern found, return current time as fallback
        return now.isoformat()
    
    @staticmethod
    def _absolutize(src: Optional[str]) -> Optional[str]:
        """Convert relative URLs to absolute."""
        if not src:
            return None
        if src.startswith("http"):
            return src
        prefix = "" if src.startswith("/") else "/"
        return f"https://musor.tv{prefix}{src}"
    
    @staticmethod
    async def _safe_click(page: Page, selector: str) -> None:
        """Safely click element if it exists."""
        try:
            el = page.locator(selector).first
            if await el.count():
                await el.click(timeout=2000)
        except Exception as e:
            logger.debug(f"Could not click element '{selector}': {e}")
            pass
    
    @staticmethod
    def _dedupe(items: List[LiveMovieRaw]) -> List[LiveMovieRaw]:
        """Remove duplicate entries."""
        seen = set()
        result = []
        for x in items:
            key = f"{x.title}|{x.channel}|{x.start_iso[:16]}"
            if key not in seen:
                seen.add(key)
                result.append(x)
        return result
    
    @staticmethod
    def _get_user_agent() -> str:
        """User agent string with valid project contact information."""
        return "Mozilla/5.0 (compatible; StremioHU/1.0; +https://github.com/radamhu/stremio-musor_tv)"
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scraper status for health monitoring.
        
        Returns:
            Dictionary with status information including:
            - healthy: bool - whether scraper is working
            - last_success_at: float or None - timestamp of last successful fetch
            - last_error_at: float or None - timestamp of last error
            - last_error: str or None - last error message
            - total_errors: int - total error count since startup
            - consecutive_errors: int - consecutive error count
        """
        return {
            "healthy": self._consecutive_error_count < 3,  # Unhealthy after 3 consecutive failures
            "last_success_at": self._last_success_at,
            "last_error_at": self._last_error_at,
            "last_error": self._last_error,
            "total_errors": self._total_error_count,
            "consecutive_errors": self._consecutive_error_count,
        }


# Singleton instance
_scraper_instance: Optional[MusorTvScraper] = None
_scraper_lock = asyncio.Lock()


async def get_scraper() -> MusorTvScraper:
    """Get or create the singleton scraper instance.
    
    Returns:
        MusorTvScraper instance
    """
    global _scraper_instance
    
    async with _scraper_lock:
        if _scraper_instance is None:
            _scraper_instance = MusorTvScraper(rate_limit_ms=RATE_MS)
            await _scraper_instance.initialize()
        return _scraper_instance


async def cleanup_scraper() -> None:
    """Cleanup the singleton scraper instance."""
    global _scraper_instance
    
    async with _scraper_lock:
        if _scraper_instance is not None:
            await _scraper_instance.cleanup()
            _scraper_instance = None


async def fetch_live_movies(force: bool = False) -> List[LiveMovieRaw]:
    """Fetch live movie data from musor.tv.
    
    Convenience function that uses the singleton scraper instance.
    
    Args:
        force: If True, bypass rate limiting and force a fresh fetch
        
    Returns:
        List of LiveMovieRaw objects
    """
    scraper = await get_scraper()
    return await scraper.fetch_live_movies(force)


async def get_scraper_status() -> Dict[str, Any]:
    """Get the current status of the scraper instance.
    
    Returns:
        Dictionary with scraper status information, or None if not initialized
    """
    global _scraper_instance
    
    async with _scraper_lock:
        if _scraper_instance is None:
            return {
                "healthy": False,
                "initialized": False,
                "message": "Scraper not yet initialized"
            }
        
        status = _scraper_instance.get_status()
        status["initialized"] = True
        return status
