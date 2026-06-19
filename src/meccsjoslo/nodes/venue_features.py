"""Venue-jelek: házigazda-előny, klíma, magasság (Story 006).

Tiszta segédfüggvények; a `derive_features` köti be őket. Az utazási
távolság/úti-pihenő NEM v1 (backlog).
"""

from __future__ import annotations

import json
from pathlib import Path

from meccsjoslo import config


def load_venues(path: Path | str = config.VENUES_FILE) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def host_advantage(
    home_tla: str,
    away_tla: str,
    host_nations: frozenset[str] = config.HOST_NATIONS,
) -> str:
    """Melyik csapat (ha van) házigazda-nemzet: home/away/both/none."""
    home_host = home_tla in host_nations
    away_host = away_tla in host_nations
    if home_host and away_host:
        return "both"
    if home_host:
        return "home"
    if away_host:
        return "away"
    return "none"


def lookup_venue(venue_name: str | None, venues: dict) -> tuple[int | None, str]:
    """(altitude_m, climate) a helyszín nevéből; ismeretlen → (None, 'unknown')."""
    info = venues.get(venue_name) if venue_name else None
    if not info:
        return None, "unknown"
    return info.get("altitude_m"), info.get("climate", "unknown")
