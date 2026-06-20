"""Egy meccs tipp.ly próbája (alapból dry-run).

Futtatás:  uv run python scripts/tipply_probe.py [home_hu] [away_hu] [hg] [ag] [--headed]
  pl.      uv run python scripts/tipply_probe.py "Németország" "Elefántcsontpart" 2 1
"""

from __future__ import annotations

import asyncio
import sys

from meccsjoslo import config
from meccsjoslo.tipply.publisher import publish_tip
from meccsjoslo.tipply.state import Match, Score


def main() -> None:
    flags = {"--headed", "--overwrite", "--submit"}
    args = [a for a in sys.argv[1:] if a not in flags]
    headed = "--headed" in sys.argv
    overwrite = "--overwrite" in sys.argv
    # Biztonság: a próba ALAPBÓL dry-run; éles mentés CSAK explicit --submit-tel
    # (a .env TIPPLY_SUBMIT-jától függetlenül).
    submit = "--submit" in sys.argv

    cfg = config.load_env()
    tcfg = config.tipply_config(cfg)
    if tcfg is None:
        raise SystemExit("Nincs TIPPLY_EMAIL/TIPPLY_PASSWORD a .env-ben.")

    home = args[0] if len(args) > 0 else "Németország"
    away = args[1] if len(args) > 1 else "Elefántcsontpart"
    hg = int(args[2]) if len(args) > 2 else 2
    ag = int(args[3]) if len(args) > 3 else 1

    print(
        f"Próba: {home} {hg}:{ag} {away}  | submit={submit} (False=dry-run)\n"
        f"storage_state: {tcfg.storage_state_path}  | base: {tcfg.base_url}\n"
    )
    report = asyncio.run(
        publish_tip(
            tcfg,
            match=Match(home=home, away=away),
            score=Score(home_goals=hg, away_goals=ag),
            submit=submit,
            overwrite=overwrite,
            headed=headed,
        )
    )
    print(f"status   : {report.status}")
    print(f"reason   : {report.reason}")
    print(f"confidence: {report.confidence}")
    print(f"screenshot: {report.screenshot}")
    if report.verify:
        print(f"readback : {report.verify.readback}")


if __name__ == "__main__":
    main()
