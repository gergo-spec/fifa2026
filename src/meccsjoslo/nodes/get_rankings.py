"""`get_rankings` node – FIFA-ranglista helyezés + pont + helyezéskülönbség.

Csapaterő kizárólag a FIFA-világranglistából (nincs Elo). A
helyezéskülönbség önálló feature: `rank_diff = away_rank - home_rank`
(pozitív → hazai erősebb).
"""

from __future__ import annotations

import json
from pathlib import Path

from meccsjoslo import config


def _load_rankings(ranking_file: Path | str) -> dict:
    data = json.loads(Path(ranking_file).read_text(encoding="utf-8"))
    return data["rankings"]


def make_get_rankings(ranking_file: Path | str = config.RANKING_FILE):
    """Node-gyár: a ranglistát egyszer betölti (cache), majd a node csak olvas."""
    rankings = _load_rankings(ranking_file)

    def get_rankings(state: dict) -> dict:
        home, away = state["home_tla"], state["away_tla"]
        hr, ar = rankings.get(home), rankings.get(away)
        update: dict = {
            "home_rank": hr["rank"] if hr else None,
            "away_rank": ar["rank"] if ar else None,
            "home_points": hr["points"] if hr else None,
            "away_points": ar["points"] if ar else None,
        }
        if hr and ar:
            update["rank_diff"] = ar["rank"] - hr["rank"]
        else:
            update["rank_diff"] = None
            missing = [tla for tla, r in ((home, hr), (away, ar)) if not r]
            update["rankings_note"] = f"ismeretlen rang a FIFA-listán: {', '.join(missing)}"
        return update

    return get_rankings
