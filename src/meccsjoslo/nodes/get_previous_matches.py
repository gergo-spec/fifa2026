"""`get_previous_matches` node – nyers korábbi meccsek + H2H.

Free tier-kompatibilis forrás: a `/matches/{id}/head2head` és a tornán belül
**FINISHED** meccsek, csapatonként `tla` szerint szűrve, frissebb elöl.
"""

from __future__ import annotations

from meccsjoslo import config


def _normalize(match: dict, tla: str) -> dict:
    """Egy meccs tömör, csapat-nézőpontú rekorddá alakítva."""
    home_tla = match["homeTeam"]["tla"]
    away_tla = match["awayTeam"]["tla"]
    full = match["score"]["fullTime"]
    if home_tla == tla:
        gf, ga, opponent, side = full["home"], full["away"], away_tla, "HOME"
    else:
        gf, ga, opponent, side = full["away"], full["home"], home_tla, "AWAY"
    result = "W" if gf > ga else "L" if gf < ga else "D"
    return {
        "utcDate": match["utcDate"],
        "side": side,
        "opponent_tla": opponent,
        "goals_for": gf,
        "goals_against": ga,
        "result": result,
    }


def _recent_for(finished: list[dict], tla: str, recent_n: int) -> list[dict]:
    involved = [
        m
        for m in finished
        if tla in (m["homeTeam"]["tla"], m["awayTeam"]["tla"])
    ]
    involved.sort(key=lambda m: m["utcDate"], reverse=True)
    return [_normalize(m, tla) for m in involved[:recent_n]]


def make_get_previous_matches(client, recent_n: int = config.RECENT_N):
    def get_previous_matches(state: dict) -> dict:
        h2h = client.head2head(state["match_id"], limit=recent_n)
        finished = client.matches(status="FINISHED")["matches"]
        return {
            "h2h": h2h,
            "home_recent_matches": _recent_for(finished, state["home_tla"], recent_n),
            "away_recent_matches": _recent_for(finished, state["away_tla"], recent_n),
        }

    return get_previous_matches
