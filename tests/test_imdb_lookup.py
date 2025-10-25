"""Unit tests for IMDb lookup functionality.

Run with: pytest tests/test_imdb_lookup.py -v
"""
import pytest
import os
import sys
from unittest.mock import patch, AsyncMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from imdb_lookup import lookup_imdb_id, batch_lookup_imdb_ids, is_lookup_enabled, get_api_status
from imdb_cache import get_cached_imdb_id, set_cached_imdb_id, clear_cache, get_cache_stats


@pytest.fixture(autouse=True)
def clear_imdb_cache():
    """Clear cache before each test."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def mock_tmdb_api_key(monkeypatch):
    """Mock TMDB API key for testing."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key_12345")
    monkeypatch.setenv("IMDB_LOOKUP_ENABLED", "true")


class TestIMDbCache:
    """Test IMDb caching functionality."""
    
    def test_cache_key_normalization(self):
        """Test that cache handles diacritics and case variations."""
        # Set cache with Hungarian title
        set_cached_imdb_id("Mátrix", 1999, "tt0133093")
        
        # Should be able to retrieve with different case/diacritics
        result1 = get_cached_imdb_id("Mátrix", 1999)
        result2 = get_cached_imdb_id("mátrix", 1999)
        result3 = get_cached_imdb_id("MÁTRIX", 1999)
        result4 = get_cached_imdb_id("Matrix", 1999)  # Without diacritics
        
        assert result1 == "tt0133093"
        assert result2 == "tt0133093"
        assert result3 == "tt0133093"
        assert result4 == "tt0133093"
    
    def test_cache_with_year(self):
        """Test cache distinguishes titles by year."""
        set_cached_imdb_id("Dune", 1984, "tt0087182")
        set_cached_imdb_id("Dune", 2021, "tt1160419")
        
        assert get_cached_imdb_id("Dune", 1984) == "tt0087182"
        assert get_cached_imdb_id("Dune", 2021) == "tt1160419"
    
    def test_cache_without_year(self):
        """Test cache works without year."""
        set_cached_imdb_id("The Matrix", None, "tt0133093")
        result = get_cached_imdb_id("The Matrix", None)
        assert result == "tt0133093"
    
    def test_cache_miss_raises_key_error(self):
        """Test cache miss raises KeyError."""
        with pytest.raises(KeyError):
            get_cached_imdb_id("Nonexistent Movie", 2025)
    
    def test_cache_none_value(self):
        """Test caching failed lookup (None value)."""
        set_cached_imdb_id("Unknown Movie", 2025, None)
        result = get_cached_imdb_id("Unknown Movie", 2025)
        assert result is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        stats = get_cache_stats()
        assert stats["size"] == 0
        assert stats["maxsize"] == 1000
        assert "ttl_days" in stats
        
        # Add some entries
        set_cached_imdb_id("Movie 1", 2020, "tt0000001")
        set_cached_imdb_id("Movie 2", 2021, "tt0000002")
        
        stats = get_cache_stats()
        assert stats["size"] == 2


class TestIMDbLookup:
    """Test IMDb lookup API integration."""
    
    @pytest.mark.asyncio
    async def test_lookup_disabled_without_api_key(self, monkeypatch):
        """Test lookup returns None when API key not configured."""
        monkeypatch.delenv("TMDB_API_KEY", raising=False)
        
        result = await lookup_imdb_id("The Matrix", 1999)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_lookup_disabled_when_flag_false(self, mock_tmdb_api_key, monkeypatch):
        """Test lookup respects IMDB_LOOKUP_ENABLED flag."""
        monkeypatch.setenv("IMDB_LOOKUP_ENABLED", "false")
        
        result = await lookup_imdb_id("The Matrix", 1999)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_lookup_uses_cache(self, mock_tmdb_api_key):
        """Test that lookup uses cache when available."""
        # Pre-populate cache
        set_cached_imdb_id("The Matrix", 1999, "tt0133093")
        
        # Should return cached value without API call
        with patch('imdb_lookup._search_movie_tmdb') as mock_search:
            result = await lookup_imdb_id("The Matrix", 1999)
            assert result == "tt0133093"
            mock_search.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_lookup_caches_result(self, mock_tmdb_api_key):
        """Test that successful lookup caches the result."""
        with patch('imdb_lookup._search_movie_tmdb', return_value=603):
            with patch('imdb_lookup._get_imdb_id_from_tmdb', return_value="tt0133093"):
                result = await lookup_imdb_id("The Matrix", 1999)
                assert result == "tt0133093"
                
                # Verify it was cached
                cached = get_cached_imdb_id("The Matrix", 1999)
                assert cached == "tt0133093"
    
    @pytest.mark.asyncio
    async def test_lookup_caches_failure(self, mock_tmdb_api_key):
        """Test that failed lookup is also cached (to avoid repeated API calls)."""
        with patch('imdb_lookup._search_movie_tmdb', return_value=None):
            result = await lookup_imdb_id("Nonexistent Movie XYZ", 2025)
            assert result is None
            
            # Verify None was cached
            cached = get_cached_imdb_id("Nonexistent Movie XYZ", 2025)
            assert cached is None
    
    @pytest.mark.asyncio
    async def test_batch_lookup(self, mock_tmdb_api_key):
        """Test batch lookup functionality."""
        movies = [
            ("The Matrix", 1999),
            ("Inception", 2010),
            ("Unknown Movie", 2025),
        ]
        
        # Mock API responses
        def mock_search(title, year, language):
            if "Matrix" in title:
                return 603
            elif "Inception" in title:
                return 27205
            else:
                return None
        
        def mock_get_imdb(tmdb_id):
            if tmdb_id == 603:
                return "tt0133093"
            elif tmdb_id == 27205:
                return "tt1375666"
            return None
        
        with patch('imdb_lookup._search_movie_tmdb', side_effect=mock_search):
            with patch('imdb_lookup._get_imdb_id_from_tmdb', side_effect=mock_get_imdb):
                results = await batch_lookup_imdb_ids(movies)
                
                assert results["The Matrix"] == "tt0133093"
                assert results["Inception"] == "tt1375666"
                assert results["Unknown Movie"] is None
    
    def test_is_lookup_enabled(self, mock_tmdb_api_key):
        """Test lookup enabled check."""
        assert is_lookup_enabled() is True
    
    def test_get_api_status(self, mock_tmdb_api_key):
        """Test API status reporting."""
        status = get_api_status()
        
        assert status["enabled"] is True
        assert status["api_key_configured"] is True
        assert "rate_limit" in status
        assert "cache" in status


class TestIMDbLookupIntegration:
    """Integration tests with mocked API responses."""
    
    @pytest.mark.asyncio
    async def test_full_lookup_flow(self, mock_tmdb_api_key):
        """Test complete lookup flow from search to IMDb ID."""
        # Mock TMDB API responses
        mock_search_response = {
            "results": [
                {
                    "id": 603,
                    "title": "The Matrix",
                    "release_date": "1999-03-31"
                }
            ]
        }
        
        mock_external_ids_response = {
            "imdb_id": "tt0133093"
        }
        
        with patch('imdb_lookup._rate_limited_request') as mock_request:
            mock_request.side_effect = [
                mock_search_response,
                mock_external_ids_response
            ]
            
            result = await lookup_imdb_id("The Matrix", 1999)
            assert result == "tt0133093"
            assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_hungarian_title_fallback_to_english(self, mock_tmdb_api_key):
        """Test that lookup tries English if Hungarian fails."""
        # First call (Hungarian) returns no results
        # Second call (English) returns results
        mock_responses = [
            {"results": []},  # Hungarian search - no results
            {"results": [{"id": 603}]},  # English search - found
            {"imdb_id": "tt0133093"}  # External IDs
        ]
        
        with patch('imdb_lookup._rate_limited_request') as mock_request:
            mock_request.side_effect = mock_responses
            
            result = await lookup_imdb_id("Mátrix", 1999)
            assert result == "tt0133093"
            # Should make 3 calls: HU search, EN search, external IDs
            assert mock_request.call_count == 3


# Run tests with: pytest tests/test_imdb_lookup.py -v
# Run with coverage: pytest tests/test_imdb_lookup.py --cov=src/imdb_lookup --cov=src/imdb_cache -v
