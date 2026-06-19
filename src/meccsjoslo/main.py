"""Napi entrypoint (Story 010).

A következő 48 óra WC-meccseit jósolja meg, és CSV-be naplóz. Cron/agent-core
indítja. A `run_once` a tesztelhető mag (injektált `now`/`sleep`); a `main` a
valós függőségeket köti be (football-data kliens + Gemini predictor).
"""

from __future__ import annotations

import contextlib
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from meccsjoslo import config
from meccsjoslo.clients.football_data import FootballDataClient
from meccsjoslo.graph import default_graph
from meccsjoslo.logging_csv import append_prediction
from meccsjoslo.nodes.predict import gemini_predictor


def _parse(utc: str) -> datetime:
    return datetime.fromisoformat(utc.replace("Z", "+00:00"))


def make_session_id(model: str, now: datetime | None = None) -> str:
    """Egy futás azonosítója – ez alá kerül a futás összes Langfuse-trace-e."""
    now = now or datetime.now(timezone.utc)
    return f"meccsjoslo-{model}-{now:%Y%m%dT%H%M%SZ}"


def session_scope(langfuse, session_id: str, model: str):
    """Context manager, ami a benne létrejövő összes span-re ráteszi a
    session_id-t (és a modell taget). Langfuse nélkül no-op."""
    if langfuse is None:
        return contextlib.nullcontext()
    from langfuse import propagate_attributes

    return propagate_attributes(session_id=session_id, tags=[f"model:{model}"])


def _input_state(match: dict, venue: str | None) -> dict:
    return {
        "match_id": match["id"],
        "utc_date": match["utcDate"],
        "stage": match["stage"],
        "group": match.get("group"),
        "home_tla": match["homeTeam"]["tla"],
        "away_tla": match["awayTeam"]["tla"],
        "home_name": match["homeTeam"]["name"],
        "away_name": match["awayTeam"]["name"],
        "competition": config.COMPETITION,
        "venue": venue,
    }


def run_once(
    client,
    graph,
    csv_path: Path | str = config.OUTPUT_CSV,
    now: datetime | None = None,
    sleep: Callable[[float], None] = time.sleep,
    run_date: str | None = None,
) -> int:
    """A következő 48h meccsei → gráf → CSV. Visszaadja a feldolgozott meccsek számát."""
    now = now or datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=48)
    run_date = run_date or now.date().isoformat()

    data = client.matches(
        date_from=now.date().isoformat(),
        date_to=(now.date() + timedelta(days=2)).isoformat(),
    )

    count = 0
    for match in data["matches"]:
        kickoff = _parse(match["utcDate"])
        if not (now <= kickoff <= cutoff):  # pontos 48h ablak
            continue
        detail = client.match(match["id"])  # a venue az egyedi meccs-lekérésben van
        state = _input_state(match, detail.get("venue"))
        result = graph.invoke(state)
        append_prediction(result, csv_path, run_date=run_date)
        count += 1
        sleep(config.RATE_LIMIT_SLEEP_S)  # rate-limit tisztelet
    return count


def main() -> None:
    cfg = config.load_env()
    model = config.gemini_model(cfg)
    client = FootballDataClient(token=config.football_data_token(cfg))
    langfuse = config.langfuse_client(cfg)
    predictor = gemini_predictor(
        model=model, api_key=config.gemini_api_key(cfg), langfuse=langfuse
    )
    graph = default_graph(client, predictor)
    session_id = make_session_id(model)
    try:
        with session_scope(langfuse, session_id, model):
            count = run_once(client, graph)
    finally:
        if langfuse is not None:
            langfuse.flush()  # a rövid életű folyamat végén kiküldjük a trace-eket
    print(f"Kész: {count} meccs megjósolva → {config.OUTPUT_CSV} (session: {session_id})")


if __name__ == "__main__":
    main()
