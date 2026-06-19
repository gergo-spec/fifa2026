"""Story 004 – get_previous_matches node."""

from meccsjoslo.clients.football_data import FootballDataClient
from meccsjoslo.nodes.get_previous_matches import make_get_previous_matches
from tests.fakes import FakeFootballDataSite


def _node(site):
    client = FootballDataClient(token="t", transport=site.transport())
    return make_get_previous_matches(client)


def _state():
    return {
        "match_id": 537401,
        "home_tla": "ECU",
        "away_tla": "CUW",
        "utc_date": "2026-06-21T00:00:00Z",
    }


def test_recent_matches_filtered_and_sorted_desc():
    out = _node(FakeFootballDataSite())(_state())
    home = out["home_recent_matches"]
    assert [m["utcDate"] for m in home] == [
        "2026-06-17T18:00:00Z",  # ECU 3-1 NOR (frissebb elöl)
        "2026-06-12T18:00:00Z",  # ECU 2-0 EGY
    ]
    assert home[0]["result"] == "W"
    assert home[0]["goals_for"] == 3 and home[0]["goals_against"] == 1
    assert home[0]["opponent_tla"] == "NOR"
    assert home[0]["side"] == "HOME"


def test_away_team_normalized_from_away_side():
    out = _node(FakeFootballDataSite())(_state())
    # CUW: NOR 1-1 CUW (vendég, D) és CUW 0-2 EGY (hazai, L)
    away = {m["utcDate"]: m for m in out["away_recent_matches"]}
    nor = away["2026-06-12T21:00:00Z"]
    assert nor["side"] == "AWAY" and nor["result"] == "D"
    assert nor["goals_for"] == 1 and nor["goals_against"] == 1


def test_h2h_aggregate_present():
    out = _node(FakeFootballDataSite())(_state())
    assert out["h2h"]["aggregates"]["numberOfMatches"] == 2


def test_no_finished_matches_yields_empty_lists():
    out = _node(FakeFootballDataSite())(
        {
            "match_id": 537401,
            "home_tla": "XYZ",
            "away_tla": "QRS",
            "utc_date": "2026-06-21T00:00:00Z",
        }
    )
    assert out["home_recent_matches"] == []
    assert out["away_recent_matches"] == []


def test_recent_limit_respected():
    client = FootballDataClient(token="t", transport=FakeFootballDataSite().transport())
    node = make_get_previous_matches(client, recent_n=1)
    out = node(_state())
    assert len(out["home_recent_matches"]) == 1
