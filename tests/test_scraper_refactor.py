"""
Tests for scraper refactor: httpx-based scraper, retry behavior, and integration mocks.
"""
import sys
import pathlib
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from scraper import MusorTvScraper, get_scraper, cleanup_scraper  # noqa: E402

FIXTURE_HTML = (
    pathlib.Path(__file__).parent / "fixtures" / "musor_filmek_sample.html"
).read_text(encoding="utf-8")


class TestScraperRefactoring:
    @pytest.mark.asyncio
    async def test_initial_state_has_no_http_client(self):
        """MusorTvScraper starts with _http_client = None (no browser startup)."""
        scraper = MusorTvScraper(rate_limit_ms=1000)
        assert scraper._http_client is None
        assert not hasattr(scraper, "_browser"), "scraper must not have a _browser attribute"
        assert not hasattr(scraper, "_playwright"), "scraper must not have a _playwright attribute"

    @pytest.mark.asyncio
    async def test_initialize_creates_http_client(self):
        """initialize() must create an httpx.AsyncClient."""
        scraper = MusorTvScraper(rate_limit_ms=1000)
        await scraper.initialize()
        try:
            assert scraper._http_client is not None
            assert isinstance(scraper._http_client, httpx.AsyncClient)
        finally:
            await scraper.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_closes_http_client(self):
        """cleanup() must set _http_client back to None."""
        scraper = MusorTvScraper(rate_limit_ms=1000)
        await scraper.initialize()
        assert scraper._http_client is not None
        await scraper.cleanup()
        assert scraper._http_client is None

    @pytest.mark.asyncio
    async def test_fetch_live_movies_returns_list(self):
        """fetch_live_movies() parses fixture HTML and returns a list."""
        scraper = MusorTvScraper(rate_limit_ms=0)
        await scraper.initialize()
        try:
            with patch.object(scraper, "_get_page", new=AsyncMock(return_value=FIXTURE_HTML)):
                result = await scraper.fetch_live_movies(force=True)
            assert isinstance(result, list)
        finally:
            await scraper.cleanup()

    @pytest.mark.asyncio
    async def test_error_counting_on_http_error(self):
        """fetch_live_movies() increments error counters when _get_page raises."""
        scraper = MusorTvScraper(rate_limit_ms=0)
        await scraper.initialize()
        try:
            with patch.object(
                scraper,
                "_get_page",
                new=AsyncMock(side_effect=httpx.HTTPError("connection refused")),
            ):
                with pytest.raises(Exception):
                    await scraper.fetch_live_movies(force=True)
            assert scraper._total_error_count == 1
            assert scraper._consecutive_error_count == 1
        finally:
            await scraper.cleanup()

    @pytest.mark.asyncio
    async def test_get_status_keys(self):
        """get_status() returns a dict with all required health keys."""
        scraper = MusorTvScraper(rate_limit_ms=0)
        status = scraper.get_status()
        expected_keys = {
            "healthy",
            "last_success_at",
            "last_error_at",
            "last_error",
            "total_errors",
            "consecutive_errors",
        }
        assert expected_keys.issubset(status.keys())

    @pytest.mark.asyncio
    async def test_singleton_returns_same_instance(self):
        """get_scraper() returns the same instance on repeated calls."""
        # Reset any existing singleton first
        await cleanup_scraper()
        try:
            scraper1 = await get_scraper()
            scraper2 = await get_scraper()
            assert scraper1 is scraper2
            assert scraper1._http_client is not None
        finally:
            await cleanup_scraper()


class TestGetPageRetryBehavior:
    """Tests for _get_page retry and failure handling using httpx mocks."""

    @pytest.mark.asyncio
    async def test_get_page_retries_and_succeeds_on_third_attempt(self):
        """_get_page retries transient HTTPErrors and returns HTML on eventual success."""
        scraper = MusorTvScraper(rate_limit_ms=0)
        await scraper.initialize()
        try:
            mock_response = MagicMock()
            mock_response.text = FIXTURE_HTML
            mock_response.raise_for_status = MagicMock()

            call_count = 0

            async def mock_get(url, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise httpx.HTTPError("transient error")
                return mock_response

            with patch.object(scraper._http_client, "get", side_effect=mock_get):
                with patch("asyncio.sleep", new=AsyncMock()):
                    result = await scraper._get_page("https://musor.tv/filmek")

            assert result == FIXTURE_HTML
            assert call_count == 3
        finally:
            await scraper.cleanup()

    @pytest.mark.asyncio
    async def test_get_page_returns_none_when_all_retries_exhausted(self):
        """_get_page returns None after all three retry attempts raise HTTPError."""
        scraper = MusorTvScraper(rate_limit_ms=0)
        await scraper.initialize()
        try:
            with patch.object(
                scraper._http_client,
                "get",
                new=AsyncMock(side_effect=httpx.HTTPError("network error")),
            ):
                with patch("asyncio.sleep", new=AsyncMock()):
                    result = await scraper._get_page("https://musor.tv/filmek")

            assert result is None
        finally:
            await scraper.cleanup()

    @pytest.mark.asyncio
    async def test_get_page_returns_none_on_http_status_error(self):
        """_get_page returns None when raise_for_status() raises HTTPStatusError."""
        scraper = MusorTvScraper(rate_limit_ms=0)
        await scraper.initialize()
        try:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=MagicMock(),
                response=MagicMock(),
            )

            with patch.object(
                scraper._http_client, "get", new=AsyncMock(return_value=mock_response)
            ):
                with patch("asyncio.sleep", new=AsyncMock()):
                    result = await scraper._get_page("https://musor.tv/filmek")

            assert result is None
        finally:
            await scraper.cleanup()


class TestFetchIntegration:
    """Integration tests: full fetch pipeline with mocked HTTP responses."""

    @pytest.mark.asyncio
    async def test_full_pipeline_returns_parsed_results(self):
        """fetch_live_movies() produces LiveMovieRaw results from mocked HTTP without live network."""
        from models import LiveMovieRaw

        scraper = MusorTvScraper(rate_limit_ms=0)
        await scraper.initialize()
        try:
            mock_response = MagicMock()
            mock_response.text = FIXTURE_HTML
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                scraper._http_client, "get", new=AsyncMock(return_value=mock_response)
            ):
                result = await scraper.fetch_live_movies(force=True)

            assert isinstance(result, list)
            assert len(result) > 0
            for item in result:
                assert isinstance(item, LiveMovieRaw)
                assert item.title
                assert item.start_iso
        finally:
            await scraper.cleanup()

    @pytest.mark.asyncio
    async def test_all_pages_unavailable_returns_empty_list(self):
        """fetch_live_movies() returns [] when all HTTP calls fail — no crash."""
        scraper = MusorTvScraper(rate_limit_ms=0)
        await scraper.initialize()
        try:
            with patch.object(
                scraper._http_client,
                "get",
                new=AsyncMock(side_effect=httpx.HTTPError("network error")),
            ):
                with patch("asyncio.sleep", new=AsyncMock()):
                    result = await scraper.fetch_live_movies(force=True)

            assert result == []
        finally:
            await scraper.cleanup()


class TestHealthStateTransitions:
    """Tests for scraper health state transitions after failures and recovery."""

    @pytest.mark.asyncio
    async def test_healthy_after_init(self):
        """Freshly initialised scraper reports healthy (no errors yet)."""
        scraper = MusorTvScraper(rate_limit_ms=0)
        assert scraper.get_status()["healthy"] is True
        assert scraper.get_status()["consecutive_errors"] == 0

    @pytest.mark.asyncio
    async def test_healthy_is_false_after_3_consecutive_failures(self):
        """healthy becomes False once consecutive error count reaches 3."""
        scraper = MusorTvScraper(rate_limit_ms=0)
        await scraper.initialize()
        try:
            for _ in range(3):
                with patch.object(
                    scraper, "_fetch", new=AsyncMock(side_effect=Exception("scraper down"))
                ):
                    with pytest.raises(Exception):
                        await scraper.fetch_live_movies(force=True)

            status = scraper.get_status()
            assert status["healthy"] is False
            assert status["consecutive_errors"] == 3
            assert status["total_errors"] == 3
        finally:
            await scraper.cleanup()

    @pytest.mark.asyncio
    async def test_healthy_resets_after_success_following_failures(self):
        """consecutive_errors resets and healthy becomes True again after a successful fetch."""
        scraper = MusorTvScraper(rate_limit_ms=0)
        await scraper.initialize()
        try:
            # Drive to unhealthy state
            for _ in range(3):
                with patch.object(
                    scraper, "_fetch", new=AsyncMock(side_effect=Exception("scraper down"))
                ):
                    with pytest.raises(Exception):
                        await scraper.fetch_live_movies(force=True)

            assert scraper.get_status()["healthy"] is False

            # One successful fetch resets consecutive_errors
            with patch.object(scraper, "_fetch", new=AsyncMock(return_value=[])):
                result = await scraper.fetch_live_movies(force=True)

            assert result == []
            status = scraper.get_status()
            assert status["healthy"] is True
            assert status["consecutive_errors"] == 0
            # Total error count is cumulative and must not reset
            assert status["total_errors"] == 3
        finally:
            await scraper.cleanup()
