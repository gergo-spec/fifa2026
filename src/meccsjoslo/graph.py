"""LangGraph összeállítás + feltételes elágazás (SPECIFICATION 5.).

```
START ─┬─> get_rankings ──────────┐
       └─> get_previous_matches ──┴─> derive_features ─┬─(GROUP_STAGE)─> get_group_standings ─┐
                                                       └─(egyébként)──────────────────────────┴─> predict ─> END
```
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from meccsjoslo import config
from meccsjoslo.nodes.derive_features import make_derive_features
from meccsjoslo.nodes.get_group_standings import make_get_group_standings
from meccsjoslo.nodes.get_previous_matches import make_get_previous_matches
from meccsjoslo.nodes.get_rankings import make_get_rankings
from meccsjoslo.nodes.predict import make_predict
from meccsjoslo.state import State


def _route_after_features(state: State) -> str:
    return "group" if state.get("stage") == "GROUP_STAGE" else "knockout"


def build_graph(
    *,
    get_rankings,
    get_previous_matches,
    derive_features,
    get_group_standings,
    predict,
):
    """Gráf injektált node-okból (teszthez mockolható)."""
    g = StateGraph(State)
    g.add_node("get_rankings", get_rankings)
    g.add_node("get_previous_matches", get_previous_matches)
    g.add_node("derive_features", derive_features)
    g.add_node("get_group_standings", get_group_standings)
    g.add_node("predict", predict)

    # párhuzamos nyersadat-ágak, fan-in a derive_features-nél
    g.add_edge(START, "get_rankings")
    g.add_edge(START, "get_previous_matches")
    g.add_edge("get_rankings", "derive_features")
    g.add_edge("get_previous_matches", "derive_features")

    # feltételes: csoportkörben extra állás-lekérés
    g.add_conditional_edges(
        "derive_features",
        _route_after_features,
        {"group": "get_group_standings", "knockout": "predict"},
    )
    g.add_edge("get_group_standings", "predict")
    g.add_edge("predict", END)
    return g.compile()


def default_graph(
    client,
    predictor,
    *,
    ranking_file=config.RANKING_FILE,
    venues_file=config.VENUES_FILE,
):
    """Éles gráf valós node-okkal (football-data kliens + Gemini predictor)."""
    return build_graph(
        get_rankings=make_get_rankings(ranking_file),
        get_previous_matches=make_get_previous_matches(client),
        derive_features=make_derive_features(venues_file=venues_file),
        get_group_standings=make_get_group_standings(client),
        predict=make_predict(predictor),
    )
