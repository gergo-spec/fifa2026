"""Story 006 – venue-jelek: házigazda, klíma, magasság."""

from meccsjoslo.nodes.derive_features import make_derive_features
from meccsjoslo.nodes.venue_features import host_advantage, load_venues, lookup_venue
from meccsjoslo import config

VENUES = config.PROJECT_ROOT / "tests" / "fixtures" / "venues.json"


def test_host_advantage_home_when_home_is_co_host():
    assert host_advantage("MEX", "ARG") == "home"


def test_host_advantage_away_when_away_is_co_host():
    assert host_advantage("ARG", "USA") == "away"


def test_host_advantage_none_when_neither():
    assert host_advantage("ESP", "KSA") == "none"


def test_host_advantage_both_when_two_co_hosts():
    assert host_advantage("USA", "MEX") == "both"


def test_lookup_known_venue():
    venues = load_venues(VENUES)
    altitude, climate = lookup_venue("Estadio Azteca", venues)
    assert altitude == 2240
    assert climate == "high-altitude"


def test_lookup_unknown_venue_is_neutral():
    venues = load_venues(VENUES)
    altitude, climate = lookup_venue("Nonexistent Park", venues)
    assert altitude is None
    assert climate == "unknown"


def test_load_venues_drops_note_key():
    venues = load_venues(VENUES)
    assert "_note" not in venues


def test_derive_features_includes_venue_signals():
    node = make_derive_features(venues_file=VENUES)
    out = node(
        {
            "utc_date": "2026-06-21T00:00:00Z",
            "venue": "Estadio Azteca",
            "home_tla": "ECU",
            "away_tla": "CUW",
            "home_recent_matches": [],
            "away_recent_matches": [],
        }
    )
    assert out["host_advantage"] == "none"
    assert out["venue_altitude_m"] == 2240
    assert out["venue_climate"] == "high-altitude"


def test_derive_features_without_venues_omits_venue_signals():
    out = make_derive_features()(
        {"utc_date": "2026-06-21T00:00:00Z", "home_recent_matches": [], "away_recent_matches": []}
    )
    assert "venue_altitude_m" not in out
