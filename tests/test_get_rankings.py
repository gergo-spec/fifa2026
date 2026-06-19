"""Story 003 – get_rankings node."""

from meccsjoslo.nodes.get_rankings import make_get_rankings


def test_known_teams_get_rank_and_diff():
    node = make_get_rankings()
    out = node({"home_tla": "ARG", "away_tla": "FRA"})
    assert out["home_rank"] == 1
    assert out["away_rank"] == 3
    # pozitív rank_diff = hazai erősebb
    assert out["rank_diff"] == 2
    assert out["home_points"] > out["away_points"]


def test_fixture_match_teams_present():
    node = make_get_rankings()
    out = node({"home_tla": "ECU", "away_tla": "CUW"})
    assert out["home_rank"] == 23
    assert out["away_rank"] == 82
    assert out["rank_diff"] == 59


def test_unknown_tla_is_none_with_note():
    node = make_get_rankings()
    out = node({"home_tla": "ARG", "away_tla": "ZZZ"})
    assert out["away_rank"] is None
    assert out["rank_diff"] is None
    assert "ZZZ" in out["rankings_note"]


def test_ranking_file_loaded_once(tmp_path):
    import json

    f = tmp_path / "r.json"
    f.write_text(
        json.dumps({"rankings": {"AAA": {"name": "A", "rank": 5, "points": 100.0}}}),
        encoding="utf-8",
    )
    node = make_get_rankings(f)
    f.unlink()  # törlés után is működnie kell (cache-elt)
    out = node({"home_tla": "AAA", "away_tla": "AAA"})
    assert out["home_rank"] == 5
