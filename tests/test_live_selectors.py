"""Live selector drift check against musor.tv. Skipped unless `--live`.

Run: python -m pytest tests/test_live_selectors.py --live -q -s
Failure means upstream markup changed: inspect HTML, update src/musor_parser.py and tests/fixtures/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx
import pytest
from selectolax.parser import HTMLParser

pytestmark = pytest.mark.live

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

FILMEK_URL = "https://musor.tv/filmek"
TVBEN_URL = "https://musor.tv/most/tvben"

# Selectors the parser relies on (see src/musor_parser.py)
FILMEK_SELECTORS = [
    "table.showeventtable",
    ".showeventtitle a",
    ".showeventtime",
    ".showeventchannel img",
]
TVBEN_SELECTORS = [
    "div[itemtype='https://schema.org/BroadcastEvent']",
    "time[itemprop='startDate']",
    "[itemprop='name']",
]


def _fetch(url: str) -> HTMLParser:
    try:
        response = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        pytest.skip(f"transport failure, not a selector problem: {exc}")
    return HTMLParser(response.text)


@pytest.mark.parametrize("selector", FILMEK_SELECTORS)
def test_filmek_selector_matches(selector):
    nodes = _fetch(FILMEK_URL).css(selector)
    print(f"{selector}: {len(nodes)}")
    assert nodes, f"{selector} matched 0 elements on {FILMEK_URL}"


@pytest.mark.parametrize("selector", TVBEN_SELECTORS)
def test_tvben_selector_matches(selector):
    nodes = _fetch(TVBEN_URL).css(selector)
    print(f"{selector}: {len(nodes)}")
    assert nodes, f"{selector} matched 0 elements on {TVBEN_URL}"
