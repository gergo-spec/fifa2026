"""Story 007 – get_group_standings node (csak nyers állás)."""

from meccsjoslo.clients.football_data import FootballDataClient
from meccsjoslo.nodes.get_group_standings import make_get_group_standings
from tests.fakes import FakeFootballDataSite


def _node():
    client = FootballDataClient(token="t", transport=FakeFootballDataSite().transport())
    return make_get_group_standings(client)


def test_selects_correct_group_table():
    out = _node()({"group": "GROUP_E", "home_tla": "ECU", "away_tla": "CUW"})
    gs = out["group_standings"]
    assert gs["group"] == "GROUP_E"
    assert len(gs["table"]) == 4


def test_identifies_both_team_rows():
    out = _node()({"group": "GROUP_E", "home_tla": "ECU", "away_tla": "CUW"})
    gs = out["group_standings"]
    assert gs["home_row"]["position"] == 1
    assert gs["home_row"]["points"] == 6
    assert gs["away_row"]["position"] == 4
    assert gs["away_row"]["points"] == 1


def test_matches_group_despite_naming_format():
    # a standings-végpont "Group E"-t ad, a meccs "GROUP_E"-t → mégis egyezzen
    class StubClient:
        def standings(self):
            return {
                "standings": [
                    {
                        "group": "Group E",
                        "table": [
                            {"team": {"tla": "ECU"}, "position": 1, "points": 6},
                            {"team": {"tla": "CUW"}, "position": 4, "points": 1},
                        ],
                    }
                ]
            }

    out = make_get_group_standings(StubClient())(
        {"group": "GROUP_E", "home_tla": "ECU", "away_tla": "CUW"}
    )
    gs = out["group_standings"]
    assert len(gs["table"]) == 2
    assert gs["home_row"]["position"] == 1
    assert gs["away_row"]["position"] == 4


def test_no_derived_motivation_only_raw():
    # a node nem számol motivációt – csak nyers állást ad (azt az LLM értelmezi)
    out = _node()({"group": "GROUP_G", "home_tla": "BEL", "away_tla": "IRN"})
    gs = out["group_standings"]
    assert "motivation" not in gs
    assert set(gs) == {"group", "table", "home_row", "away_row"}
