"""Verify node – a kitöltött gól-inputok visszaolvasása és összevetése."""

from __future__ import annotations

from meccsjoslo.tipply.state import LocatePlan, VerifyResult


async def verify(browser, plan: LocatePlan) -> VerifyResult:
    """Minden kitöltött gól-input visszaolvasása és összevetése a szándékkal."""
    readback: dict[str, dict[str, str | None]] = {}
    ok = True
    for action in plan.actions:
        if action.kind != "fill":
            continue
        label = action.locator.value
        actual = await browser.read_back(action.locator)
        readback[label] = {"expected": action.value, "actual": actual}
        if actual != action.value:
            ok = False
    return VerifyResult(ok=ok, readback=readback)
