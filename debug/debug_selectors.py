"""Debug script to inspect musor.tv HTML structure using httpx + selectolax."""
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


def inspect_page(url: str) -> None:
    """Inspect page structure to find correct selectors."""
    print(f"\n{'='*80}")
    print(f"Inspecting: {url}")
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

    selectors = [
        "table.showeventtable",
        ".showeventtitle a",
        ".showeventtime",
        ".showeventchannel img",
        "td[itemprop='description']",
        "img.showeventimg",
        "div[itemtype='https://schema.org/BroadcastEvent']",
        "time[itemprop='startDate']",
        "[itemprop='name']",
    ]

    print("\nSelector counts:")
    for sel in selectors:
        nodes = tree.css(sel)
        if nodes:
            print(f"  ✓ {sel}: {len(nodes)} elements")
            first = nodes[0]
            print(f"    tag={first.tag}  attrs={dict(first.attributes)}")
            text = first.text(strip=True)
            if text:
                print(f"    text: {text[:120]}")
        else:
            print(f"  - {sel}: 0 elements")


def main() -> None:
    for url in ["https://musor.tv/filmek", "https://musor.tv/most/tvben"]:
        inspect_page(url)


if __name__ == "__main__":
    main()
