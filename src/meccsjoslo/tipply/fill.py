"""Fill node – a megtalált action-terv végrehajtása a böngészőn (fill mód)."""

from __future__ import annotations

from meccsjoslo.tipply.fixtures import located_fixture_matches
from meccsjoslo.tipply.locate import locate_match
from meccsjoslo.tipply.state import FillReport, LocatePlan, Match, Score, VerifyResult
from meccsjoslo.tipply.submit import submit_tip
from meccsjoslo.tipply.verify import verify


async def fill_tip(browser, plan: LocatePlan) -> None:
    """A megtalált action-terv determinisztikus végrehajtása a böngésző-porton."""
    for action in plan.actions:
        await browser.act(action)


async def fill_and_verify(
    browser,
    llm,
    *,
    match: Match,
    score: Score,
    submit: bool = False,
    overwrite: bool = False,
    confidence_threshold: float = 0.6,
    max_locate_attempts: int = 2,
    screenshot_path: str = "fill.png",
) -> FillReport:
    """Fill-mód: locate → fill → verify, korlátos loop-back eltérésnél.

    Dry-run alapból: sosem submit-el; mindig készít screenshotot a kitöltésről.
    ``submit=True`` esetén beküld és újraolvas. Idempotens: létező tippet
    ``overwrite=True`` nélkül kihagy.
    """
    result = None
    plan: LocatePlan | None = None

    for attempt in range(max_locate_attempts):
        if await browser.is_bot_walled():
            await browser.screenshot(screenshot_path)
            return FillReport(status="needs_human", screenshot=screenshot_path, reason="bot_wall")

        snapshot = await browser.snapshot()
        plan = await locate_match(llm, match=match, score=score, snapshot=snapshot)

        fills = [a for a in plan.actions if a.kind == "fill"]
        if not fills or plan.confidence < confidence_threshold:
            await browser.screenshot(screenshot_path)
            return FillReport(
                status="needs_human",
                confidence=plan.confidence,
                plan=plan,
                screenshot=screenshot_path,
                reason="no_match" if not fills else "low_confidence",
            )

        if not located_fixture_matches(snapshot, match, plan):
            await browser.screenshot(screenshot_path)
            return FillReport(
                status="needs_human",
                confidence=plan.confidence,
                plan=plan,
                screenshot=screenshot_path,
                reason="fixture_mismatch",
            )

        if attempt == 0 and not overwrite:
            existing = await _existing_tip(browser, plan)
            if existing is not None:
                await browser.screenshot(screenshot_path)
                return FillReport(
                    status="skipped",
                    confidence=plan.confidence,
                    verify=existing,
                    plan=plan,
                    screenshot=screenshot_path,
                )

        await fill_tip(browser, plan)
        result = await verify(browser, plan)
        if result.ok:
            status = "filled"
            if submit:
                result = await submit_tip(browser, plan)
                status = "submitted" if result.ok else "needs_human"
            await browser.screenshot(screenshot_path)
            return FillReport(
                status=status,
                confidence=plan.confidence,
                verify=result,
                plan=plan,
                screenshot=screenshot_path,
            )

    await browser.screenshot(screenshot_path)
    return FillReport(
        status="needs_human",
        confidence=plan.confidence if plan else 0.0,
        verify=result,
        plan=plan,
        screenshot=screenshot_path,
    )


async def _existing_tip(browser, plan: LocatePlan) -> VerifyResult | None:
    """A gól-inputok olvasása; visszaadja a read-backet, ha már van tipp."""
    readback: dict[str, dict[str, str | None]] = {}
    present = True
    for action in plan.actions:
        if action.kind != "fill":
            continue
        actual = await browser.read_back(action.locator)
        readback[action.locator.value] = {"expected": action.value, "actual": actual}
        if actual in (None, ""):
            present = False
    return VerifyResult(ok=False, readback=readback) if present and readback else None
