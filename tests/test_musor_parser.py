"""Tests for src/musor_parser.py — pure parser, no network access."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime
import pytest
import musor_parser
from musor_parser import (
    parse_filmek,
    cleanup,
    infer_start_iso,
    absolutize,
    dedupe,
)
from models import LiveMovieRaw

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "musor_filmek_sample.html"


@pytest.fixture
def filmek_html() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


@pytest.fixture
def filmek_entries(filmek_html: str) -> list:
    return parse_filmek(filmek_html)


# ---------------------------------------------------------------------------
# parse_filmek — fixture-based
# ---------------------------------------------------------------------------

def test_parse_filmek_returns_five_entries(filmek_entries):
    assert len(filmek_entries) == 5


def test_parse_filmek_fields(filmek_entries):
    first = filmek_entries[0]
    assert first.title
    assert first.start_iso
    assert first.channel
    # start_iso must be a valid ISO datetime
    datetime.fromisoformat(first.start_iso)


def test_parse_filmek_poster_absolute(filmek_entries):
    for entry in filmek_entries:
        if entry.poster is not None:
            assert entry.poster.startswith("https://"), (
                f"Expected absolute URL, got: {entry.poster}"
            )


def test_parse_filmek_category_optional(filmek_entries):
    # No entry should cause a crash; category is None or a non-empty string
    for entry in filmek_entries:
        assert entry.category is None or isinstance(entry.category, str)


def test_parse_filmek_empty_html():
    assert parse_filmek("") == []


def test_parse_filmek_no_tables():
    assert parse_filmek("<html><body></body></html>") == []


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------

def test_cleanup_whitespace():
    assert cleanup("  hello   world  ") == "hello world"
    assert cleanup("foo\t\nbar") == "foo bar"


def test_cleanup_none():
    assert cleanup(None) == ""


# ---------------------------------------------------------------------------
# infer_start_iso
# ---------------------------------------------------------------------------

def test_infer_start_iso_full_format():
    result = infer_start_iso("2025.10.18 22:30")
    assert "2025-10-18" in result
    assert "22:30" in result


def test_infer_start_iso_time_only():
    result = infer_start_iso("14:30")
    assert "14:30" in result
    # Must be parseable as ISO
    datetime.fromisoformat(result)


# ---------------------------------------------------------------------------
# absolutize
# ---------------------------------------------------------------------------

def test_absolutize_relative_slash():
    assert absolutize("/image.jpg") == "https://musor.tv/image.jpg"


def test_absolutize_relative_no_slash():
    assert absolutize("image.jpg") == "https://musor.tv/image.jpg"


def test_absolutize_absolute():
    url = "https://example.com/img.jpg"
    assert absolutize(url) == url


def test_absolutize_none():
    assert absolutize(None) is None


# ---------------------------------------------------------------------------
# dedupe
# ---------------------------------------------------------------------------

def _make_entry(title: str, channel: str, start_iso: str) -> LiveMovieRaw:
    return LiveMovieRaw(title=title, start_iso=start_iso, channel=channel)


def test_dedupe_removes_duplicates():
    entry = _make_entry("Film", "RTL", "2025-10-18T22:30:00")
    duplicate = _make_entry("Film", "RTL", "2025-10-18T22:30:00")
    result = dedupe([entry, duplicate])
    assert len(result) == 1


def test_dedupe_keeps_unique():
    a = _make_entry("Film A", "RTL", "2025-10-18T22:30:00")
    b = _make_entry("Film B", "RTL", "2025-10-18T22:30:00")
    c = _make_entry("Film A", "TV2", "2025-10-18T22:30:00")
    result = dedupe([a, b, c])
    assert len(result) == 3


# ---------------------------------------------------------------------------
# infer_start_iso — malformed / edge inputs
# ---------------------------------------------------------------------------

def test_infer_start_iso_empty_string_returns_iso():
    """Empty string has no time pattern; must return current-time ISO without raising."""
    result = infer_start_iso("")
    # Must be parseable as ISO datetime
    datetime.fromisoformat(result)


def test_infer_start_iso_garbage_returns_iso():
    """Garbage text with no time pattern must return current-time ISO without raising."""
    result = infer_start_iso("ez nem idő")
    datetime.fromisoformat(result)


def test_infer_start_iso_partial_match_uses_time():
    """Text containing only 'HH:MM' is parsed correctly."""
    result = infer_start_iso("műsor: 09:00 kezdés")
    assert "09:00" in result
    datetime.fromisoformat(result)


# ---------------------------------------------------------------------------
# parse_filmek — resilience: per-entry error does not abort whole scrape
# ---------------------------------------------------------------------------

def test_parse_filmek_entry_error_does_not_abort(filmek_html: str, monkeypatch):
    """A parse error on one entry must be skipped; remaining entries still return."""
    call_count = 0
    original_infer = musor_parser.infer_start_iso

    def patched_infer(time_text: str) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("injected parse error on first entry")
        return original_infer(time_text)

    monkeypatch.setattr(musor_parser, "infer_start_iso", patched_infer)

    results = parse_filmek(filmek_html)
    # First entry fails; the other four must still parse successfully
    assert len(results) == 4
