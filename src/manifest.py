"""Stremio addon manifest configuration."""

MANIFEST = {
    "id": "hu.live.movies",
    "version": "1.0.0",
    "name": "HU Live Movies (musor.tv)",
    "description": "Discover movies on Hungarian TV • Works with your stream addons",
    "logo": "https://stremio-logo.svg",  # replace if you have one
    "behaviorHints": {"configurable": False},
    "resources": ["catalog", "stream"],
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
