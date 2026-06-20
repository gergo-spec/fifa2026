"""A következő N óra WC-meccseinek élesben jóslása (valós football-data + Gemini).

Futtatás:  uv run python scripts/predict_window.py [órák] [modell]
  pl.      uv run python scripts/predict_window.py 36
           uv run python scripts/predict_window.py 36 gemini-3.5-flash
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from meccsjoslo import config
from meccsjoslo.clients.football_data import FootballDataClient
from meccsjoslo.graph import default_graph
from meccsjoslo.main import combine_results, make_session_id, run_once, session_scope
from meccsjoslo.nodes.predict import gemini_predictor
from meccsjoslo.tipply.sink import make_tipply_sink


class MemoizingClient:
    """Azonos GET-ek cache-elve (rate-limit kímélés)."""

    def __init__(self, inner):
        self._inner = inner
        self._cache: dict = {}

    def get(self, path, params=None):
        key = (path, tuple(sorted((params or {}).items())))
        if key not in self._cache:
            self._cache[key] = self._inner.get(path, params)
        return self._cache[key]

    def __getattr__(self, name):
        return getattr(self._inner, name)


def main() -> None:
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 36
    cfg = config.load_env()
    model = sys.argv[2] if len(sys.argv) > 2 else config.gemini_model(cfg)

    client = MemoizingClient(
        FootballDataClient(token=config.football_data_token(cfg), max_retries=5)
    )
    langfuse = config.langfuse_client(cfg)
    predictor = gemini_predictor(
        model=model, api_key=config.gemini_api_key(cfg), langfuse=langfuse
    )
    graph = default_graph(client, predictor)

    sink = make_tipply_sink(cfg)  # opcionális tipp.ly publikálás
    now = datetime.now(timezone.utc)
    session_id = make_session_id(model)
    out_csv = config.PROJECT_ROOT / f"predictions_next{hours}h.csv"
    print(
        f"Most (UTC): {now:%Y-%m-%d %H:%M}  |  ablak: {hours} óra  |  modell: {model}\n"
        f"Kimenet: {out_csv}  |  Langfuse: {'bekötve' if langfuse else '-'}  |  "
        f"session: {session_id if langfuse else '-'}  |  "
        f"tipp.ly: {'bekötve' if sink else '-'}\n"
    )

    def show(r: dict) -> None:
        print(
            f"✓ {r['utc_date']} | {r.get('stage')} {r.get('group') or ''} | "
            f"{r['home_name']} vs {r['away_name']}\n"
            f"   P(H/X/V) = {r['prob_home']:.2f} / {r['prob_draw']:.2f} / {r['prob_away']:.2f}"
            f"  | xG {r['expected_goals_home']:.1f}-{r['expected_goals_away']:.1f}"
            f"  | FIFA #{r.get('home_rank')} vs #{r.get('away_rank')}\n"
            f"   {r['rationale']}\n"
        )

    try:
        with session_scope(langfuse, session_id, model):
            count = run_once(
                client, graph, csv_path=out_csv, now=now,
                window_hours=hours, on_result=combine_results(show, sink),
            )
    finally:
        if langfuse is not None:
            langfuse.flush()

    print(f"Kész: {count} meccs a következő {hours} órában → {out_csv}")


if __name__ == "__main__":
    main()
