"""A node-ok közt vándorló közös állapot (SPECIFICATION 3.)."""

from __future__ import annotations

from typing import TypedDict


class State(TypedDict, total=False):
    # --- bemenet ---
    match_id: int
    utc_date: str
    home_tla: str
    away_tla: str
    home_name: str
    away_name: str
    stage: str
    group: str | None
    venue: str | None
    competition: str

    # --- nyersadat ---
    home_rank: int | None
    away_rank: int | None
    home_points: float | None
    away_points: float | None
    rank_diff: int | None
    rankings_note: str
    home_recent_matches: list
    away_recent_matches: list
    h2h: dict
    group_standings: dict

    # --- származtatott jellemzők ---
    home_form: dict
    away_form: dict
    home_goals: dict
    away_goals: dict
    home_fatigue: dict
    away_fatigue: dict
    host_advantage: str
    venue_altitude_m: int | None
    venue_climate: str

    # --- kimenet ---
    prob_home: float
    prob_draw: float
    prob_away: float
    expected_goals_home: float
    expected_goals_away: float
    rationale: str
