"""Pure HTML parser for musor.tv pages. No network access, no asyncio."""
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from selectolax.parser import HTMLParser
from models import LiveMovieRaw

logger = logging.getLogger(__name__)


def cleanup(s: Optional[str]) -> str:
    """Strip and collapse whitespace."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def infer_start_iso(time_text: str) -> str:
    """Parse musor.tv datetime format with midnight boundary handling.

    Handles two formats:
    1. Full datetime: '2025.10.18 22:30' (always accurate)
    2. Time only: '01:30' (uses day boundary detection)

    For time-only formats, if the parsed time is more than 12 hours in the past,
    we assume it refers to the next day (handles late-night programs).
    """
    # Try full datetime format first: YYYY.MM.DD HH:MM
    match = re.search(r"(\d{4})\.(\d{2})\.(\d{2})\s+(\d{1,2}):(\d{2})", time_text)
    if match:
        year, month, day, hour, minute = match.groups()
        d = datetime(int(year), int(month), int(day), int(hour), int(minute))
        return d.isoformat()

    # Fallback: HH:MM only - detect day boundary
    match = re.search(r"(\d{1,2}):(\d{2})", time_text)
    now = datetime.now()

    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        d = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If the time is significantly in the past (> 12 hours), assume next day
        time_diff = (d - now).total_seconds()
        if time_diff < -12 * 3600:
            d = d + timedelta(days=1)
            logger.debug(
                f"Adjusted date for time '{time_text}': crossed midnight boundary "
                f"(now={now.strftime('%H:%M')}, parsed={hour:02d}:{minute:02d})"
            )

        return d.isoformat()

    # No time pattern found, return current time as fallback
    return now.isoformat()


def absolutize(src: Optional[str]) -> Optional[str]:
    """Convert relative URLs to absolute musor.tv URLs."""
    if not src:
        return None
    if src.startswith("http"):
        return src
    prefix = "" if src.startswith("/") else "/"
    return f"https://musor.tv{prefix}{src}"


def dedupe(items: List[LiveMovieRaw]) -> List[LiveMovieRaw]:
    """Remove duplicate entries based on title+channel+start_iso[:16]."""
    seen: set = set()
    result: List[LiveMovieRaw] = []
    for x in items:
        key = f"{x.title}|{x.channel}|{x.start_iso[:16]}"
        if key not in seen:
            seen.add(key)
            result.append(x)
    return result


def parse_filmek(html: str) -> List[LiveMovieRaw]:
    """Parse /filmek page HTML and return a flat list of LiveMovieRaw entries.

    Does not deduplicate — caller decides.
    Logs a warning and continues on per-entry parse errors.
    """
    if not html:
        return []

    tree = HTMLParser(html)
    tables = tree.css("table.showeventtable")

    results: List[LiveMovieRaw] = []
    for table in tables:
        try:
            # Title
            title_node = table.css_first(".showeventtitle a")
            title = cleanup(title_node.text(strip=True) if title_node else None)
            if not title:
                continue

            # Start time
            time_node = table.css_first(".showeventtime")
            time_text = cleanup(time_node.text(strip=True) if time_node else None)
            start_iso = infer_start_iso(time_text)

            # Channel (from img alt attribute in .showeventchannel)
            channel_img = table.css_first(".showeventchannel img")
            channel = cleanup(
                channel_img.attributes.get("alt") if channel_img else None
            )

            # Category (optional)
            cat_node = table.css_first('td[itemprop="description"]')
            category: Optional[str] = cleanup(
                cat_node.text(strip=True) if cat_node else None
            ) or None

            # Poster (optional, relative URL → absolutize)
            poster_img = table.css_first("img.showeventimg")
            poster: Optional[str] = absolutize(
                poster_img.attributes.get("src") if poster_img else None
            )

            results.append(
                LiveMovieRaw(
                    title=title,
                    start_iso=start_iso,
                    channel=channel,
                    category=category,
                    poster=poster,
                )
            )
        except Exception as exc:
            logger.warning(f"Skipping entry due to parse error: {exc}")
            continue

    return results
