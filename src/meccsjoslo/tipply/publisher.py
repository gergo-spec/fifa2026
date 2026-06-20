"""Slim publish-belépő: login → /hu/bets → fill_and_verify → (submit).

A `tipply_publisher.run_fill` magja, a `runs/` artefakt-réteg nélkül; egy
screenshotot ment a `tipply_runs/<ts>/` alá.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from meccsjoslo import config as mc_config
from meccsjoslo.tipply.config import TipplyConfig
from meccsjoslo.tipply.fill import fill_and_verify
from meccsjoslo.tipply.login import ensure_authenticated
from meccsjoslo.tipply.state import FillReport, Match, Score


async def publish_tip(
    config: TipplyConfig,
    *,
    match: Match,
    score: Score,
    submit: bool = False,
    overwrite: bool = False,
    headed: bool = False,
    llm=None,
    browser=None,
) -> FillReport:
    """Egy tipp feltöltése (dry-run alapból). A `llm`/`browser` injektálható teszthez."""
    from meccsjoslo.tipply.browser import PlaywrightBrowser
    from meccsjoslo.tipply.llm import LangchainLocateLLM

    browser = browser or PlaywrightBrowser(headed=headed)
    llm = llm or LangchainLocateLLM()

    run_dir = mc_config.PROJECT_ROOT / "tipply_runs" / datetime.now().strftime("%Y%m%dT%H%M%S_%f")
    run_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = str(run_dir / "fill.png")

    report = FillReport(status="needs_human", reason="error")
    try:
        await ensure_authenticated(browser, config)
        await browser.goto(config.bets_url)
        report = await fill_and_verify(
            browser,
            llm,
            match=match,
            score=score,
            submit=submit,
            overwrite=overwrite,
            screenshot_path=screenshot_path,
        )
    except Exception as err:  # mindig riportot adunk
        report = FillReport(
            status="needs_human", reason=f"error: {type(err).__name__}: {err}"
        )
    finally:
        try:
            await browser.close()
        except Exception:
            pass
    return report
