"""Debug script v2 — inspect musor.tv program elements using httpx + selectolax."""
import sys
import httpx
from selectolax.parser import HTMLParser

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

FILMEK_URL = "https://musor.tv/filmek"
TVBEN_URL = "https://musor.tv/most/tvben"


def find_programs(url: str) -> None:
    """Find actual program/show elements using plain HTTP."""
    print(f"\n{'='*80}")
    print(f"Analyzing: {url}")
    print("="*80)

    try:
        response = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"HTTP error: {exc}")
        return

    html = response.text
    tree = HTMLParser(html)
    print(f"Status: {response.status_code}  Size: {len(html)} bytes")

    # filmek table entries
    tables = tree.css("table.showeventtable")
    print(f"\ntable.showeventtable: {len(tables)} entries")
    for node in tables[:3]:
        title_node = node.css_first(".showeventtitle a")
        time_node = node.css_first(".showeventtime")
        channel_node = node.css_first(".showeventchannel img")
        title = title_node.text(strip=True) if title_node else "—"
        time_text = time_node.text(strip=True) if time_node else "—"
        channel = channel_node.attributes.get("alt", "—") if channel_node else "—"
        print(f"  title={title!r}  time={time_text!r}  channel={channel!r}")

    # EPG BroadcastEvent entries (tvben page)
    events = tree.css("div[itemtype='https://schema.org/BroadcastEvent']")
    print(f"\nBroadcastEvent entries: {len(events)}")
    for node in events[:3]:
        name_node = node.css_first("[itemprop='name']")
        time_node = node.css_first("time[itemprop='startDate']")
        name = name_node.text(strip=True) if name_node else "—"
        start = time_node.attributes.get("content", "—") if time_node else "—"
        print(f"  name={name!r}  startDate={start!r}")

    # Program-related links (first 10)
    links = tree.css("a[href*='/musor/']")
    print(f"\nProgram links (/musor/): {len(links)}")
    for node in links[:10]:
        href = node.attributes.get("href", "")
        text = node.text(strip=True)
        print(f"  href={href!r}  text={text!r}")


def main() -> None:
    find_programs(FILMEK_URL)
    find_programs(TVBEN_URL)


if __name__ == "__main__":
    main()
