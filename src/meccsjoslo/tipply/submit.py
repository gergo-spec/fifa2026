"""Submit node – determinisztikus tipp-beküldés + utólagos visszaolvasás."""

from __future__ import annotations

from meccsjoslo.tipply.state import LocatePlan, VerifyResult
from meccsjoslo.tipply.verify import verify


async def submit_tip(browser, plan: LocatePlan) -> VerifyResult:
    """Determinisztikus beküldés, majd visszaolvasás a mentett eredményhez."""
    await browser.submit()
    return await verify(browser, plan)
