"""Éles futtatás a 4 tesztesetre (valós football-data + valós Gemini).

A nodes több azonos lekérést indítana (FINISHED meccsek, csoportállás) → egy
memoizáló réteggel beférünk a 10 kérés/perc keretbe.

Futtatás:  uv run python scripts/live_predict.py [modell]
  pl.     uv run python scripts/live_predict.py gemini-3.5-flash
"""

from __future__ import annotations

import sys

from meccsjoslo import config
from meccsjoslo.clients.football_data import FootballDataClient
from meccsjoslo.graph import default_graph
from meccsjoslo.logging_csv import append_prediction
from meccsjoslo.main import _input_state
from meccsjoslo.nodes.predict import gemini_predictor

# A 4 teszteset valós football-data match ID-ja (2026-06-21).
MATCH_IDS = [537354, 537360, 537371, 537365]


class MemoizingClient:
    """A FootballDataClient köré: azonos GET-ek cache-elve (rate-limit kímélés)."""

    def __init__(self, inner: FootballDataClient):
        self._inner = inner
        self._cache: dict = {}

    def get(self, path, params=None):
        key = (path, tuple(sorted((params or {}).items())))
        if key not in self._cache:
            self._cache[key] = self._inner.get(path, params)
        return self._cache[key]

    def __getattr__(self, name):
        return getattr(self._inner, name)


def _predict_match(graph, state, label, langfuse):
    """A teljes meccs-gráfot egy Langfuse szülő-span alá rendezi (az LLM-hívás
    generation-ként ez alá ágyazódik)."""
    if langfuse is None:
        return graph.invoke(state)
    with langfuse.start_as_current_observation(
        name=f"meccsjoslo: {label}", as_type="chain", input=state
    ) as span:
        result = graph.invoke(state)
        span.update(
            output={
                "prob_home": result["prob_home"],
                "prob_draw": result["prob_draw"],
                "prob_away": result["prob_away"],
                "expected_goals_home": result["expected_goals_home"],
                "expected_goals_away": result["expected_goals_away"],
            }
        )
        return result


def main() -> None:
    cfg = config.load_env()
    model = sys.argv[1] if len(sys.argv) > 1 else config.gemini_model(cfg)
    client = MemoizingClient(
        FootballDataClient(token=config.football_data_token(cfg), max_retries=5)
    )
    langfuse = config.langfuse_client(cfg)
    predictor = gemini_predictor(
        model=model, api_key=config.gemini_api_key(cfg), langfuse=langfuse
    )
    graph = default_graph(client, predictor)

    safe = model.replace(".", "_").replace("/", "_")
    out_csv = config.PROJECT_ROOT / f"predictions_live_{safe}.csv"
    print(
        f"Modell: {model}\nKimenet: {out_csv}\n"
        f"Langfuse: {'bekötve' if langfuse else 'nincs konfigurálva'}\n"
    )

    for match_id in MATCH_IDS:
        detail = client.match(match_id)
        state = _input_state(detail, detail.get("venue"))
        label = f"{state['home_name']} vs {state['away_name']} ({state.get('group')})"
        try:
            result = _predict_match(graph, state, label, langfuse)
        except Exception as exc:  # pl. modell-404 vagy LLM hiba
            print(f"✗ {label}: HIBA – {type(exc).__name__}: {exc}\n")
            continue

        append_prediction(result, out_csv)
        print(
            f"✓ {label}\n"
            f"   FIFA: #{result.get('home_rank')} vs #{result.get('away_rank')} "
            f"(diff {result.get('rank_diff')}) | venue: {state.get('venue')} "
            f"({result.get('venue_climate')}, {result.get('venue_altitude_m')} m)\n"
            f"   P(hazai/döntetlen/vendég) = "
            f"{result['prob_home']:.2f} / {result['prob_draw']:.2f} / {result['prob_away']:.2f}\n"
            f"   Várható gól: {result['expected_goals_home']:.1f} - {result['expected_goals_away']:.1f}\n"
            f"   Indoklás: {result['rationale']}\n"
        )

    if langfuse is not None:
        langfuse.flush()  # trace-ek kiküldése a rövid életű folyamat végén
        print("Langfuse: trace-ek elküldve.")


if __name__ == "__main__":
    main()
