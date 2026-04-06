"""Dump live musor.tv HTML to file using plain HTTP (httpx).

Usage:
    python debug/dump_html.py

Outputs:
    /tmp/musor_filmek.html
    /tmp/musor_tvben.html
"""
import pathlib
import httpx

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

PAGES = {
    "filmek": "https://musor.tv/filmek",
    "tvben": "https://musor.tv/most/tvben",
}


def dump_html(name: str, url: str) -> None:
    """Fetch URL and save HTML to /tmp."""
    try:
        response = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"✗ {url}: {exc}")
        return

    html = response.text
    filename = pathlib.Path(f"/tmp/musor_{name}.html")
    filename.write_text(html, encoding="utf-8")

    print(f"✓ {url}")
    print(f"  Saved: {filename}")
    print(f"  Size:  {len(html)} bytes  ({len(html)//1024} KB)")

    for keyword in ("showeventtable", "BroadcastEvent", "film", "csatorna"):
        count = html.lower().count(keyword.lower())
        if count:
            print(f"  '{keyword}' occurrences: {count}")


def main() -> None:
    for name, url in PAGES.items():
        dump_html(name, url)


if __name__ == "__main__":
    main()
