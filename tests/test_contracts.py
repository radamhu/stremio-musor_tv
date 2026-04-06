"""Contract tests — protect Stremio addon catalog and meta payload shapes.

These tests verify that:
  - catalog responses always return {"metas": [...]} with stable field shapes
  - meta responses always return {"meta": ...} with stable field shapes
  - ID formats remain compatible with current consumers
  - error paths degrade gracefully instead of raising to the caller
"""
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models import LiveMovieRaw

# ---------------------------------------------------------------------------
# Shared fixture movie — category must pass is_probably_film() ("film" in text)
# ---------------------------------------------------------------------------

_FIXTURE_ISO = datetime(2026, 4, 6, 14, 0, 0).isoformat()

_FIXTURE_MOVIE = LiveMovieRaw(
    title="Teszt Akciófilm",
    start_iso=_FIXTURE_ISO,
    channel="RTL",
    category="akciófilm,2020",
    poster="https://musor.tv/img/test.jpg",
)


# ---------------------------------------------------------------------------
# Catalog contract tests
# ---------------------------------------------------------------------------


class TestCatalogContract:
    """catalog_handler must always return {"metas": [...]} with stable field shapes."""

    @pytest.mark.asyncio
    async def test_catalog_response_has_metas_key(self):
        """Top-level response must be a dict with a "metas" key containing a list."""
        with patch("catalog_handler.fetch_live_movies", new=AsyncMock(return_value=[_FIXTURE_MOVIE])):
            with patch("catalog_handler.within_window", return_value=True):
                with patch("catalog_handler._cache") as mock_cache:
                    mock_cache.get.return_value = None
                    mock_cache.set.return_value = None
                    from catalog_handler import catalog_handler

                    result = await catalog_handler("movie", "hu-live", {})

        assert "metas" in result
        assert isinstance(result["metas"], list)

    @pytest.mark.asyncio
    async def test_catalog_each_meta_has_required_fields(self):
        """Every meta item in the catalog must have id, type, and name."""
        with patch("catalog_handler.fetch_live_movies", new=AsyncMock(return_value=[_FIXTURE_MOVIE])):
            with patch("catalog_handler.within_window", return_value=True):
                with patch("catalog_handler._cache") as mock_cache:
                    mock_cache.get.return_value = None
                    mock_cache.set.return_value = None
                    with patch("catalog_handler.is_lookup_enabled", return_value=False):
                        from catalog_handler import catalog_handler

                        result = await catalog_handler("movie", "hu-live", {})

        assert len(result["metas"]) > 0, "Fixture movie must produce at least one meta entry"
        for meta in result["metas"]:
            assert "id" in meta, f"Missing 'id' in meta: {meta}"
            assert "type" in meta, f"Missing 'type' in meta: {meta}"
            assert "name" in meta, f"Missing 'name' in meta: {meta}"
            assert meta["type"] == "movie"
            assert meta["name"]

    @pytest.mark.asyncio
    async def test_catalog_id_format_is_musortv_or_imdb(self):
        """ID must be musortv:-prefixed (no IMDb lookup) or tt-prefixed (IMDb)."""
        with patch("catalog_handler.fetch_live_movies", new=AsyncMock(return_value=[_FIXTURE_MOVIE])):
            with patch("catalog_handler.within_window", return_value=True):
                with patch("catalog_handler._cache") as mock_cache:
                    mock_cache.get.return_value = None
                    mock_cache.set.return_value = None
                    with patch("catalog_handler.is_lookup_enabled", return_value=False):
                        from catalog_handler import catalog_handler

                        result = await catalog_handler("movie", "hu-live", {})

        for meta in result["metas"]:
            id_ = meta["id"]
            is_musortv = id_.startswith("musortv:")
            is_imdb = id_.startswith("tt") and id_[2:].isdigit()
            assert is_musortv or is_imdb, f"Unexpected ID format: {id_!r}"

    @pytest.mark.asyncio
    async def test_catalog_musortv_id_has_4_colon_parts(self):
        """musortv: IDs must split into exactly 4 colon-separated parts."""
        with patch("catalog_handler.fetch_live_movies", new=AsyncMock(return_value=[_FIXTURE_MOVIE])):
            with patch("catalog_handler.within_window", return_value=True):
                with patch("catalog_handler._cache") as mock_cache:
                    mock_cache.get.return_value = None
                    mock_cache.set.return_value = None
                    with patch("catalog_handler.is_lookup_enabled", return_value=False):
                        from catalog_handler import catalog_handler

                        result = await catalog_handler("movie", "hu-live", {})

        for meta in result["metas"]:
            id_ = meta["id"]
            if id_.startswith("musortv:"):
                parts = id_.split(":")
                assert len(parts) == 4, (
                    f"Expected 4 colon-separated parts in musortv ID, got {len(parts)}: {id_!r}"
                )
                _, channel_slug, timestamp_str, title_slug = parts
                assert timestamp_str.isdigit(), (
                    f"Timestamp slot must be numeric digits: {timestamp_str!r} in {id_!r}"
                )

    @pytest.mark.asyncio
    async def test_catalog_unknown_type_returns_empty_metas(self):
        """Non-movie type must return {"metas": []} without hitting the scraper."""
        from catalog_handler import catalog_handler

        result = await catalog_handler("series", "hu-live", {})
        assert result == {"metas": []}

    @pytest.mark.asyncio
    async def test_catalog_unknown_catalog_id_returns_empty_metas(self):
        """Unknown catalog ID must return {"metas": []}."""
        from catalog_handler import catalog_handler

        result = await catalog_handler("movie", "unknown-catalog", {})
        assert result == {"metas": []}

    @pytest.mark.asyncio
    async def test_catalog_scraper_failure_returns_empty_not_raises(self):
        """Scraper failure must degrade to empty metas — must not propagate an exception."""
        with patch("catalog_handler.fetch_live_movies", new=AsyncMock(side_effect=Exception("scraper down"))):
            with patch("catalog_handler._cache") as mock_cache:
                mock_cache.get.return_value = None
                mock_cache.set.return_value = None
                from catalog_handler import catalog_handler

                result = await catalog_handler("movie", "hu-live", {})

        assert result == {"metas": []}


# ---------------------------------------------------------------------------
# Meta contract tests
# ---------------------------------------------------------------------------


class TestMetaContract:
    """meta_handler must always return {"meta": ...} or {"meta": None} — never raise."""

    @pytest.mark.asyncio
    async def test_meta_response_has_meta_key(self):
        """Top-level response must be a dict with a "meta" key."""
        from meta_handler import meta_handler

        result = await meta_handler("movie", "musortv:rtl:9999999999:ghost-id")
        assert "meta" in result

    @pytest.mark.asyncio
    async def test_meta_non_movie_type_returns_none(self):
        """Non-movie type must yield {"meta": None}."""
        from meta_handler import meta_handler

        result = await meta_handler("series", "musortv:rtl:1234567890:any-film")
        assert result == {"meta": None}

    @pytest.mark.asyncio
    async def test_meta_invalid_id_format_returns_none(self):
        """Unrecognised ID format must yield {"meta": None} without raising."""
        from meta_handler import meta_handler

        result = await meta_handler("movie", "not-a-valid-id")
        assert result == {"meta": None}

    @pytest.mark.asyncio
    async def test_meta_no_match_returns_none(self):
        """ID that matches no live movie must yield {"meta": None}."""
        meta_id = "musortv:nonexistent:9999999999:no-such-film"
        with patch("meta_handler.fetch_live_movies", new=AsyncMock(return_value=[_FIXTURE_MOVIE])):
            from meta_handler import meta_handler

            result = await meta_handler("movie", meta_id)

        assert result.get("meta") is None

    @pytest.mark.asyncio
    async def test_meta_matched_entry_has_required_fields(self):
        """Matched meta must contain id, type, and name with correct values."""
        from utils import slugify

        ts = int(datetime.fromisoformat(_FIXTURE_MOVIE.start_iso.replace("Z", "+00:00")).timestamp())
        meta_id = (
            f"musortv:{slugify(_FIXTURE_MOVIE.channel)}:{ts}:{slugify(_FIXTURE_MOVIE.title)}"
        )

        with patch("meta_handler.fetch_live_movies", new=AsyncMock(return_value=[_FIXTURE_MOVIE])):
            with patch("meta_handler.is_lookup_enabled", return_value=False):
                from meta_handler import meta_handler

                result = await meta_handler("movie", meta_id)

        meta = result.get("meta")
        assert meta is not None, "Expected a matched meta, got None"
        assert meta.get("id") == meta_id
        assert meta.get("type") == "movie"
        assert meta.get("name") == _FIXTURE_MOVIE.title

    @pytest.mark.asyncio
    async def test_meta_scraper_failure_returns_none_not_raises(self):
        """Scraper failure in meta path must degrade to {"meta": None}."""
        from utils import slugify

        ts = int(datetime.fromisoformat(_FIXTURE_MOVIE.start_iso.replace("Z", "+00:00")).timestamp())
        meta_id = (
            f"musortv:{slugify(_FIXTURE_MOVIE.channel)}:{ts}:{slugify(_FIXTURE_MOVIE.title)}"
        )

        with patch("meta_handler.fetch_live_movies", new=AsyncMock(side_effect=Exception("net error"))):
            from meta_handler import meta_handler

            result = await meta_handler("movie", meta_id)

        assert result == {"meta": None}


# ---------------------------------------------------------------------------
# ID format contract — parse_meta_id unit tests
# ---------------------------------------------------------------------------


class TestParseMetaId:
    """parse_meta_id must correctly parse valid IDs and reject invalid ones."""

    def test_valid_id_parses_all_components(self):
        from meta_handler import parse_meta_id

        result = parse_meta_id("musortv:rtl:1744027200:teszt-film")
        assert result is not None
        assert result["channel_slug"] == "rtl"
        assert result["timestamp"] == "1744027200"
        assert result["title_slug"] == "teszt-film"

    def test_missing_prefix_returns_none(self):
        from meta_handler import parse_meta_id

        assert parse_meta_id("rtl:1744027200:teszt-film") is None

    def test_wrong_part_count_returns_none(self):
        from meta_handler import parse_meta_id

        assert parse_meta_id("musortv:rtl:teszt-film") is None
        assert parse_meta_id("musortv:rtl:1744027200:film:extra") is None

    def test_non_numeric_timestamp_returns_none(self):
        from meta_handler import parse_meta_id

        assert parse_meta_id("musortv:rtl:not-a-number:teszt-film") is None

    def test_imdb_id_format_not_parsed_as_musortv(self):
        """IMDb IDs (tt…) must be handled elsewhere; parse_meta_id must reject them."""
        from meta_handler import parse_meta_id

        assert parse_meta_id("tt1234567") is None
