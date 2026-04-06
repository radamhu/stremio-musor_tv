"""Web scraper for musor.tv live movies."""
import asyncio
import os
import logging
from typing import Optional, List, Any, Dict
import httpx
from models import LiveMovieRaw
from musor_parser import parse_filmek, dedupe


logger = logging.getLogger(__name__)

# Configuration
RATE_MS = int(os.getenv("SCRAPE_RATE_MS", "30000"))

_USER_AGENT = "Mozilla/5.0 (compatible; StremioHU/1.0; +https://github.com/radamhu/stremio-musor_tv)"

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
        self._http_client: Optional[httpx.AsyncClient] = None
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
        """Initialize the HTTP client."""
        if self._http_client is None:
            logger.info("Initializing httpx client...")
            self._http_client = httpx.AsyncClient(
                headers={"User-Agent": _USER_AGENT},
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
            )
            logger.info("HTTP client initialized successfully")
    
    async def cleanup(self) -> None:
        """Cleanup HTTP client resources."""
        if self._http_client:
            logger.info("Closing HTTP client...")
            await self._http_client.aclose()
            self._http_client = None
            
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
        """Internal method to perform the actual scraping."""
        logger.info("Starting fetch_live_movies...")
        await self.initialize()

        results: List[LiveMovieRaw] = []

        for url in PAGES:
            logger.info(f"Scraping {url}")
            html = await self._get_page(url)
            if html is None:
                logger.warning(f"Skipping {url}: no HTML retrieved")
                continue
            page_results = parse_filmek(html)
            logger.info(f"Parsed {len(page_results)} items from {url}")
            results.extend(page_results)

        logger.info(f"Total raw results before deduplication: {len(results)}")
        deduplicated = dedupe(results)
        logger.info(f"Total results after deduplication: {len(deduplicated)}")
        return deduplicated

    async def _get_page(self, url: str) -> Optional[str]:
        """Fetch a page with retry logic.

        Args:
            url: The URL to fetch.

        Returns:
            HTML text on success, None if all retries fail.
        """
        if self._http_client is None:
            await self.initialize()
        assert self._http_client is not None

        max_retries = 3
        retry_delays = [2, 4]  # seconds between attempt 1→2 and 2→3

        for attempt in range(max_retries):
            try:
                logger.info(f"Loading {url} (attempt {attempt + 1}/{max_retries})")
                response = await self._http_client.get(url)
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)

        logger.error(f"All {max_retries} attempts failed for {url}")
        return None

    @staticmethod
    def _get_user_agent() -> str:
        """User agent string."""
        return _USER_AGENT
    
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
