"""Stremio addon manifest configuration."""

MANIFEST = {
    "id": "hu.live.movies",
    "version": "1.0.0",
    "name": "HU Live Movies (musor.tv)",
    "description": "TV schedule discovery addon - finds what's on Hungarian TV (streams provided by your other addons)",
    "logo": "https://stremio-logo.svg",  # replace if you have one
    "behaviorHints": {"configurable": False},
    "resources": ["catalog", "meta"],
    "types": ["movie"],
    "catalogs": [{
        "type": "movie",
        "id": "hu-live",
        "name": "Live on TV (HU)",
        "extra": [
            {"name": "search", "isRequired": False},
            {"name": "time", "options": ["now", "next2h", "tonight"], "isRequired": False}
        ]
    }]
}
