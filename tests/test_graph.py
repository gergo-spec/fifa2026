"""Story 008 – gráf összeállítás + feltételes elágazás."""

import pytest

from meccsjoslo.graph import build_graph


def _instrumented():
    """Mock node-ok, amik naplózzák a meglátogatást."""
    visited = []

    def make(name, result=None):
        def node(state):
            visited.append(name)
            return result or {}
        return node

    graph = build_graph(
        get_rankings=make("get_rankings", {"home_rank": 1}),
        get_previous_matches=make("get_previous_matches", {"h2h": {}}),
        derive_features=make("derive_features", {"home_form": {}}),
        get_group_standings=make("get_group_standings", {"group_standings": {}}),
        predict=make("predict", {"prob_home": 0.5, "prob_draw": 0.3, "prob_away": 0.2}),
    )
    return graph, visited


def _input(stage, group=None):
    return {
        "match_id": 1, "utc_date": "2026-06-21T00:00:00Z",
        "home_tla": "ECU", "away_tla": "CUW", "stage": stage, "group": group,
    }


def test_group_stage_runs_standings_before_predict():
    graph, visited = _instrumented()
    out = graph.invoke(_input("GROUP_STAGE", "GROUP_E"))
    assert "get_group_standings" in visited
    assert visited.index("get_group_standings") < visited.index("predict")
    assert out["prob_home"] == 0.5


def test_knockout_skips_group_standings():
    graph, visited = _instrumented()
    graph.invoke(_input("LAST_16"))
    assert "get_group_standings" not in visited
    assert "predict" in visited


def test_both_raw_nodes_run_before_derive_features():
    graph, visited = _instrumented()
    graph.invoke(_input("GROUP_STAGE", "GROUP_E"))
    assert {"get_rankings", "get_previous_matches"} <= set(visited)
    assert visited.index("derive_features") > visited.index("get_rankings")
    assert visited.index("derive_features") > visited.index("get_previous_matches")


def test_state_is_merged_from_all_nodes():
    graph, _ = _instrumented()
    out = graph.invoke(_input("GROUP_STAGE", "GROUP_E"))
    # mindkét párhuzamos ág írása megmarad
    assert out["home_rank"] == 1
    assert out["h2h"] == {}
    assert "group_standings" in out
