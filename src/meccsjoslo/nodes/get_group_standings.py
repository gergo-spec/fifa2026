"""`get_group_standings` node – a meccs csoportjának NYERS tabellája.

Csak csoportkörben fut (a gráf feltételes éle vezérli). Szándékosan nem számol
motivációt: a forgatókönyv-értelmezést (továbbjutott / kiesett / gólkülönbség
kell) az LLM végzi a predict node-ban.
"""

from __future__ import annotations

import re


def _norm_group(group: str | None) -> str:
    """A csoportnév normalizálása: a meccs-végpont `GROUP_E`, a standings-végpont
    `"Group E"` formátumot ad → mindkettő `groupe` lesz."""
    return re.sub(r"[^a-z0-9]", "", (group or "").lower())


def _find_row(table: list[dict], tla: str) -> dict | None:
    return next((row for row in table if row["team"]["tla"] == tla), None)


def make_get_group_standings(client):
    def get_group_standings(state: dict) -> dict:
        group = state["group"]
        standings = client.standings()["standings"]
        table = next(
            (s["table"] for s in standings if _norm_group(s.get("group")) == _norm_group(group)),
            [],
        )
        return {
            "group_standings": {
                "group": group,
                "table": table,
                "home_row": _find_row(table, state["home_tla"]),
                "away_row": _find_row(table, state["away_tla"]),
            }
        }

    return get_group_standings
