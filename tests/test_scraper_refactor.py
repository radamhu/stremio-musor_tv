"""
Simple tests to verify the scraper refactoring works correctly.

Run with: pytest tests/test_scraper_refactor.py -v
"""
import pytest
import asyncio
from src.scraper import MusorTvScraper, get_scraper, fetch_live_movies, cleanup_scraper


class TestScraperRefactoring:
    """Tests for the refactored MusorTvScraper class."""
    
    @pytest.mark.asyncio
    async def test_scraper_initialization(self):
        """Test that scraper initializes and cleans up properly."""
        scraper = MusorTvScraper(rate_limit_ms=1000)
        
        # Should not be initialized yet
        assert scraper._browser is None
        assert scraper._playwright is None
        
        # Initialize
        await scraper.initialize()
        assert scraper._browser is not None
        assert scraper._playwright is not None
        
        # Cleanup
        await scraper.cleanup()
        assert scraper._browser is None
        assert scraper._playwright is None
    
    @pytest.mark.asyncio
    async def test_scraper_thread_safety(self):
        """Test that concurrent fetches are handled safely."""
        scraper = MusorTvScraper(rate_limit_ms=1000)
        await scraper.initialize()
        
        try:
            # Launch multiple concurrent fetches
            tasks = [scraper.fetch_live_movies() for _ in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed (no race conditions)
            for result in results:
                assert not isinstance(result, Exception)
                assert isinstance(result, list)
            
            # All results should be identical (reused in-flight fetch)
            first_result = results[0]
            for result in results[1:]:
                assert result == first_result
                
        finally:
            await scraper.cleanup()
    
    @pytest.mark.asyncio
    async def test_scraper_rate_limiting(self):
        """Test that rate limiting works correctly."""
        import time
        
        scraper = MusorTvScraper(rate_limit_ms=500)
        await scraper.initialize()
        
        try:
            # First fetch
            start = time.time()
            await scraper.fetch_live_movies(force=False)
            
            # Second fetch should be rate limited if forced
            await scraper.fetch_live_movies(force=True)
            elapsed = time.time() - start
            
            # Should have waited at least 500ms
            assert elapsed >= 0.5
            
        finally:
            await scraper.cleanup()
    
    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test that get_scraper() returns singleton instance."""
        scraper1 = await get_scraper()
        scraper2 = await get_scraper()
        
        # Should be the same instance
        assert scraper1 is scraper2
        assert scraper1._browser is not None
        
        # Cleanup
        await cleanup_scraper()
    
    @pytest.mark.asyncio
    async def test_backward_compatibility(self):
        """Test that the old API still works."""
        # This should work exactly as before
        movies = await fetch_live_movies(force=False)
        
        # Should return a list
        assert isinstance(movies, list)
        
        # Cleanup
        await cleanup_scraper()
    
    @pytest.mark.asyncio
    async def test_multiple_initializations(self):
        """Test that multiple initialize calls don't create multiple browsers."""
        scraper = MusorTvScraper()
        
        await scraper.initialize()
        browser1 = scraper._browser
        
        # Second initialize should not create new browser
        await scraper.initialize()
        browser2 = scraper._browser
        
        assert browser1 is browser2
        
        await scraper.cleanup()
    
    @pytest.mark.asyncio
    async def test_cleanup_idempotent(self):
        """Test that cleanup can be called multiple times safely."""
        scraper = MusorTvScraper()
        await scraper.initialize()
        
        # First cleanup
        await scraper.cleanup()
        assert scraper._browser is None
        
        # Second cleanup should not raise error
        await scraper.cleanup()
        assert scraper._browser is None


class TestScraperHelperMethods:
    """Tests for scraper helper methods."""
    
    def test_cleanup_string(self):
        """Test string cleanup."""
        assert MusorTvScraper._cleanup("  Hello   World  ") == "Hello World"
        assert MusorTvScraper._cleanup("\n\tTest\n") == "Test"
        assert MusorTvScraper._cleanup(None) == ""
        assert MusorTvScraper._cleanup("") == ""
    
    def test_infer_start_iso_full_format(self):
        """Test parsing full datetime format."""
        result = MusorTvScraper._infer_start_iso("2025.10.18 22:30")
        assert "2025-10-18" in result
        assert "22:30" in result
    
    def test_infer_start_iso_time_only(self):
        """Test parsing time only format."""
        result = MusorTvScraper._infer_start_iso("14:30")
        assert "14:30" in result
    
    def test_absolutize_url(self):
        """Test URL absolutization."""
        assert MusorTvScraper._absolutize("/image.jpg") == "https://musor.tv/image.jpg"
        assert MusorTvScraper._absolutize("image.jpg") == "https://musor.tv/image.jpg"
        assert MusorTvScraper._absolutize("https://example.com/img.jpg") == "https://example.com/img.jpg"
        assert MusorTvScraper._absolutize(None) is None
    
    def test_dedupe(self):
        """Test deduplication logic."""
        from src.models import LiveMovieRaw
        
        items = [
            LiveMovieRaw(
                title="Movie 1",
                start_iso="2025-10-18T22:00:00",
                channel="TV1",
                category="Film",
                poster=None
            ),
            LiveMovieRaw(
                title="Movie 1",
                start_iso="2025-10-18T22:00:00",
                channel="TV1",
                category="Film",
                poster=None
            ),
            LiveMovieRaw(
                title="Movie 2",
                start_iso="2025-10-18T23:00:00",
                channel="TV2",
                category="Film",
                poster=None
            ),
        ]
        
        result = MusorTvScraper._dedupe(items)
        assert len(result) == 2
        assert result[0].title == "Movie 1"
        assert result[1].title == "Movie 2"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
