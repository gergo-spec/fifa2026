"""Egy predictions CSV sorait felteszi a tipp.ly-ra (alapból DRY-RUN).

A már megjósolt meccseket (CSV) publikálja – újrajóslás nélkül. Biztonságos
teszthez: submit csak explicit `--submit` kapcsolóval (a .env TIPPLY_SUBMIT-tól
függetlenül).

Futtatás:  uv run python scripts/tipply_publish_csv.py [csv] [--submit] [--overwrite]
"""

from __future__ import annotations

import asyncio
import csv
import sys
import time

from meccsjoslo import config
from meccsjoslo.notify import make_notifier, notify_started, notify_tip
from meccsjoslo.tipply.publisher import publish_tip
from meccsjoslo.tipply.sink import load_team_names_hu
from meccsjoslo.tipply.state import Match, Score


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    submit = "--submit" in sys.argv
    overwrite = "--overwrite" in sys.argv
    csv_path = args[0] if args else str(config.PROJECT_ROOT / "predictions_next48h.csv")

    cfg = config.load_env()
    tcfg = config.tipply_config(cfg)
    if tcfg is None:
        raise SystemExit("Nincs TIPPLY_EMAIL/TIPPLY_PASSWORD a .env-ben.")
    names = load_team_names_hu()

    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    mode = "ÉLES SUBMIT" if submit else "dry-run"
    print(f"CSV: {csv_path}  | {len(rows)} meccs  | mód: {mode}  | overwrite: {overwrite}\n")

    notifier = make_notifier(cfg)
    notify_started(notifier, f"CSV publikálás ({mode}), {len(rows)} meccs")

    for r in rows:
        home = names.get(r["home_tla"], r["home_name"])
        away = names.get(r["away_tla"], r["away_name"])
        score = Score(
            home_goals=int(round(float(r["expected_goals_home"]))),
            away_goals=int(round(float(r["expected_goals_away"]))),
        )
        report = asyncio.run(
            publish_tip(
                tcfg,
                match=Match(home=home, away=away),
                score=score,
                submit=submit,
                overwrite=overwrite,
            )
        )
        reason = f" ({report.reason})" if report.reason else ""
        print(f"  {home} {score.home_goals}:{score.away_goals} {away} -> {report.status}{reason}", flush=True)
        notify_tip(notifier, home, away, score, report.status)
        time.sleep(3)


if __name__ == "__main__":
    main()
