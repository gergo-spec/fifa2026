"""Opcionális tipp.ly sink – a kész jóslatot (pontos eredmény) felteszi tipp.ly-ra.

A `run_once(on_result=...)` horogba köthető. Kapuzott: `None`-t ad (no-op), ha a
`TIPPLY_PUBLISH` ki van kapcsolva vagy nincs tipp.ly-konfiguráció. A tényleges
böngésző-publikálás injektálható (`publish`), így a sink böngésző nélkül tesztelhető.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from meccsjoslo import config
from meccsjoslo.tipply.state import Match, Score

_TEAMS_HU = config.PROJECT_ROOT / "data" / "teams_hu.json"


def load_team_names_hu(path: Path | str = _TEAMS_HU) -> dict[str, str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _default_publish(tcfg, match: Match, score: Score, submit: bool):
    """Éles publikálás: a slim publisher futtatása saját event loopban."""
    import asyncio

    from meccsjoslo.tipply.publisher import publish_tip

    return asyncio.run(
        publish_tip(tcfg, match=match, score=score, submit=submit)
    )


def make_tipply_sink(
    cfg: dict[str, str] | None = None,
    *,
    publish: Callable = _default_publish,
    sleep: Callable[[float], None] = time.sleep,
    pace_s: float = 4.0,
    team_names: dict[str, str] | None = None,
    notifier=None,
) -> Callable[[dict], None] | None:
    """`on_result` callback, vagy `None` ha a publikálás nincs bekapcsolva.

    Ha `notifier` kapott, meccsenként egy ntfy.sh értesítést is küld a tippről.
    """
    cfg = cfg if cfg is not None else config.load_env()
    if not config.tipply_publish_enabled(cfg):
        return None
    tcfg = config.tipply_config(cfg)
    if tcfg is None:
        return None

    submit = config.tipply_submit_enabled(cfg)
    names = team_names if team_names is not None else load_team_names_hu()

    def on_result(result: dict) -> None:
        from meccsjoslo.notify import notify_tip

        home = names.get(result["home_tla"], result.get("home_name"))
        away = names.get(result["away_tla"], result.get("away_name"))
        match = Match(home=home, away=away)
        score = Score(
            home_goals=round(float(result["expected_goals_home"])),
            away_goals=round(float(result["expected_goals_away"])),
        )
        report = publish(tcfg, match, score, submit)
        suffix = f" ({report.reason})" if getattr(report, "reason", None) else ""
        print(
            f"   tipp.ly: {home} {score.home_goals}:{score.away_goals} {away}"
            f" -> {report.status}{suffix}"
        )
        notify_tip(notifier, home, away, score, report.status)
        sleep(pace_s)  # ember-tempó a böngésző-sessionök közt

    return on_result
