"""Browser port + helyi Playwright backend.

Az egész publikálás a :class:`Browser` protokollon keresztül vezérli a
böngészőt, így a helyi Playwright backend később lecserélhető. A unit tesztek
ugyanezt a felületet megvalósító in-memory fake-et használnak.

MEGJEGYZÉS: a tipp.ly login-gated, ezért az itteni szelektorok/heurisztikák
(submit gomb, bot-wall jelek) provizórikusak, élesben igazolandók.
"""

from __future__ import annotations

import json
import re
from typing import Protocol

from meccsjoslo.tipply.snapshot import clamp_snapshot
from meccsjoslo.tipply.state import Action, Locator


class Browser(Protocol):
    async def open(self, storage_state: str | None = None) -> None: ...
    async def goto(self, url: str) -> None: ...
    async def current_url(self) -> str: ...
    async def fill(self, selector: str, value: str) -> None: ...
    async def set_checkbox(self, selector: str, checked: bool) -> None: ...
    async def click(self, selector: str) -> None: ...
    async def save_storage_state(self, path: str) -> None: ...
    async def snapshot(self) -> str: ...
    async def act(self, action: Action) -> None: ...
    async def read_back(self, locator: Locator) -> str | None: ...
    async def screenshot(self, path: str) -> None: ...
    async def submit(self) -> None: ...
    async def is_bot_walled(self) -> bool: ...
    async def start_trace(self) -> None: ...
    async def stop_trace(self, path: str) -> None: ...
    async def close(self) -> None: ...


# CAPTCHA / bot-wall jelek (ne kerüld meg – állj meg).
_BOT_WALL_SELECTORS = (
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    "iframe[title*='captcha' i]",
    ".cf-challenge",
    "#challenge-form",
)
# A determinisztikus "mentés/beküldés" kontroll (magyar UI).
_SUBMIT_NAME = re.compile(r"\b(ment|küld|mentés|beküld|submit|save)\b", re.IGNORECASE)

# Fixture-kinyerés {home, away, home_input, away_input} alakban. A tipp.ly minden
# gól-inputot `bets[<matchId>][home_scores|away_scores]` néven ad; a két csapat
# logó alt-szövege adja a home (első) és away (második) nevet – stabil horgony.
_FIXTURES_JS = r"""() => {
  const out = [], seen = new Set();
  for (const inp of document.querySelectorAll("input[name^='bets['][name*='home_scores']")) {
    const m = inp.name.match(/bets\[(\d+)\]/);
    if (!m) continue;
    const id = m[1];
    if (seen.has(id)) continue;
    seen.add(id);
    const homeName = `bets[${id}][home_scores]`, awayName = `bets[${id}][away_scores]`;
    const hasCard = (el) =>
      el.querySelectorAll(`input[name='${homeName}'],input[name='${awayName}']`).length >= 2 &&
      el.querySelectorAll('img[alt]').length >= 2;
    let c = inp;
    for (let i = 0; i < 10 && c && !hasCard(c); i++) c = c.parentElement;
    if (!c || !hasCard(c)) continue;
    const alts = [...c.querySelectorAll('img[alt]')].map(i => i.alt.trim()).filter(Boolean);
    out.push({ home: alts[0] || null, away: alts[1] || null,
               home_input: homeName, away_input: awayName });
  }
  return out;
}"""


class PlaywrightBrowser:
    """Helyi Chromium backend, headed debughoz."""

    def __init__(self, headed: bool = False):
        self.headed = headed
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._tracing = False

    @property
    def is_open(self) -> bool:
        return self._context is not None

    async def open(self, storage_state: str | None = None) -> None:
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=not self.headed)
        kwargs = {"storage_state": storage_state} if storage_state else {}
        self._context = await self._browser.new_context(**kwargs)
        self._page = await self._context.new_page()

    async def goto(self, url: str) -> None:
        await self._page.goto(url, wait_until="domcontentloaded")

    async def current_url(self) -> str:
        return self._page.url

    # --- determinisztikus login form -----------------------------------------

    async def fill(self, selector: str, value: str) -> None:
        await self._page.fill(selector, value)

    async def set_checkbox(self, selector: str, checked: bool) -> None:
        await self._page.set_checked(selector, checked)

    async def click(self, selector: str) -> None:
        await self._page.click(selector)

    async def save_storage_state(self, path: str) -> None:
        await self._context.storage_state(path=path)

    # --- locate / fill / verify ----------------------------------------------

    def _locator(self, locator: Locator):
        page = self._page
        match locator.strategy:
            case "role":
                if locator.name:
                    return page.get_by_role(locator.value, name=locator.name)
                return page.get_by_role(locator.value)
            case "label":
                return page.get_by_label(locator.value)
            case "text":
                return page.get_by_text(locator.value)
            case "placeholder":
                return page.get_by_placeholder(locator.value)
            case "xpath":
                return page.locator(f"xpath={locator.value}")
            case _:  # "css"
                return page.locator(locator.value)

    async def snapshot(self) -> str:
        fixtures = await self._page.evaluate(_FIXTURES_JS)
        if fixtures:
            return clamp_snapshot(json.dumps({"fixtures": fixtures}, ensure_ascii=False))
        raw = await self._page.locator("body").aria_snapshot()
        return clamp_snapshot(raw)

    async def act(self, action: Action) -> None:
        loc = self._locator(action.locator).first
        if action.kind == "fill":
            await loc.fill(action.value or "")
        elif action.kind == "click":
            await loc.click()
        elif action.kind == "select":
            await loc.select_option(action.value or "")

    async def read_back(self, locator: Locator) -> str | None:
        loc = self._locator(locator).first
        try:
            return await loc.input_value()
        except Exception:
            return None

    async def screenshot(self, path: str) -> None:
        await self._page.screenshot(path=path, full_page=True)

    async def submit(self) -> None:
        btn = self._page.get_by_role("button", name="Mentés")
        if await btn.count() == 0:
            btn = self._page.get_by_role("button", name=_SUBMIT_NAME)
        await btn.first.click()
        try:
            await self._page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

    async def is_bot_walled(self) -> bool:
        for selector in _BOT_WALL_SELECTORS:
            if await self._page.locator(selector).count() > 0:
                return True
        return False

    # --- tracing / teardown ---------------------------------------------------

    async def start_trace(self) -> None:
        await self._context.tracing.start(screenshots=True, snapshots=True)
        self._tracing = True

    async def stop_trace(self, path: str) -> None:
        if self._tracing:
            await self._context.tracing.stop(path=path)
            self._tracing = False

    async def close(self) -> None:
        if self._context is not None:
            await self._context.close()
        if self._browser is not None:
            await self._browser.close()
        if self._pw is not None:
            await self._pw.stop()
        self._context = self._browser = self._pw = self._page = None
