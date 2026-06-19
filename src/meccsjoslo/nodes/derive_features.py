"""`derive_features` node – determinisztikus jelek a nyers meccsekből.

Három fő jel mindkét csapatra: **forma** (frissebb meccs nagyobb súllyal),
**fáradtság** (pihenőnapok + meccssűrűség; utazási távolság NINCS v1-ben) és
**gólok** (lőtt/kapott gólátlag). A venue-jeleket (házigazda, klíma, magasság)
a Story 006 köti ide.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from meccsjoslo import config
from meccsjoslo.nodes.venue_features import host_advantage, load_venues, lookup_venue

_POINTS = {"W": 3, "D": 1, "L": 0}
_MAX_RECENT = 5


def _parse(utc: str) -> datetime:
    return datetime.fromisoformat(utc.replace("Z", "+00:00"))


def _form(matches: list[dict]) -> dict:
    games = matches[:_MAX_RECENT]
    n = len(games)
    if n == 0:
        return {"weighted": None, "win_rate": None, "sample_size": 0, "insufficient": True}
    # frissebb meccs nagyobb súllyal: [n, n-1, ..., 1]
    weights = list(range(n, 0, -1))
    weight_sum = sum(weights)
    weighted_points = sum(w * _POINTS[g["result"]] for w, g in zip(weights, games))
    weighted = weighted_points / (3 * weight_sum)
    win_rate = sum(1 for g in games if g["result"] == "W") / n
    return {
        "weighted": round(weighted, 4),
        "win_rate": round(win_rate, 4),
        "sample_size": n,
        "insufficient": n < 2,
    }


def _goals(matches: list[dict]) -> dict:
    games = matches[:_MAX_RECENT]
    n = len(games)
    if n == 0:
        return {"attack": None, "defense": None, "sample_size": 0, "insufficient": True}
    attack = sum(g["goals_for"] for g in games) / n
    defense = sum(g["goals_against"] for g in games) / n
    return {
        "attack": round(attack, 3),
        "defense": round(defense, 3),
        "sample_size": n,
        "insufficient": n < 2,
    }


def _fatigue(matches: list[dict], ref_date: str, window_days: int) -> dict:
    if not matches:
        return {"rest_days": None, "matches_in_window": 0, "insufficient": True}
    ref = _parse(ref_date)
    last = _parse(matches[0]["utcDate"])  # a lista frissebb-elöl rendezett
    rest_days = (ref - last).days
    window_start = ref - timedelta(days=window_days)
    in_window = sum(1 for m in matches if _parse(m["utcDate"]) >= window_start)
    return {
        "rest_days": rest_days,
        "matches_in_window": in_window,
        "insufficient": False,
    }


def make_derive_features(
    window_days: int = config.FORM_WINDOW_DAYS,
    venues_file: Path | str | None = None,
):
    """Node-gyár. Ha `venues_file` adott, a venue-jelek (házigazda, klíma,
    magasság – Story 006) is bekerülnek a kimenetbe."""
    venues = load_venues(venues_file) if venues_file else None

    def derive_features(state: dict) -> dict:
        ref = state["utc_date"]
        home = state.get("home_recent_matches", [])
        away = state.get("away_recent_matches", [])
        out = {
            "home_form": _form(home),
            "away_form": _form(away),
            "home_goals": _goals(home),
            "away_goals": _goals(away),
            "home_fatigue": _fatigue(home, ref, window_days),
            "away_fatigue": _fatigue(away, ref, window_days),
        }
        if venues is not None:
            altitude, climate = lookup_venue(state.get("venue"), venues)
            out["host_advantage"] = host_advantage(state["home_tla"], state["away_tla"])
            out["venue_altitude_m"] = altitude
            out["venue_climate"] = climate
        return out

    return derive_features
