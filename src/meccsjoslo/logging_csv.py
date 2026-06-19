"""Jóslat → CSV append (Story 010).

Stabil oszlopsorrend (SPECIFICATION 7.) – egy külön repó tooljának kell majd
kiértékelnie (Brier), ezért a séma nem változhat. Tizedes pont, UTF-8, a
szöveges mezők (pl. rationale) szükség szerint idézőjelezve.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from meccsjoslo import config

COLUMNS = [
    "run_date",
    "match_id",
    "utc_date",
    "stage",
    "group",
    "home_tla",
    "away_tla",
    "home_name",
    "away_name",
    "home_rank",
    "away_rank",
    "rank_diff",
    "prob_home",
    "prob_draw",
    "prob_away",
    "expected_goals_home",
    "expected_goals_away",
    "rationale",
]


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def append_prediction(
    state: dict,
    path: Path | str = config.OUTPUT_CSV,
    run_date: str | None = None,
) -> None:
    """Egy jóslatsor hozzáfűzése; a fejléc csak új/üres fájlnál íródik."""
    path = Path(path)
    run_date = run_date or _today_utc()
    row = {col: ("" if state.get(col) is None else state.get(col)) for col in COLUMNS}
    row["run_date"] = run_date
    # a következő layer egész gólszámot vár (a Langfuse-logban marad a float)
    for col in ("expected_goals_home", "expected_goals_away"):
        if row[col] != "":
            row[col] = int(round(float(row[col])))

    is_new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
