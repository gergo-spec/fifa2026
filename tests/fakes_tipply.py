"""In-memory fake-ek a tipp.ly publikálás teszteléséhez (böngésző/hálózat nélkül)."""

from __future__ import annotations


class FakeBrowser:
    """A Browser portot megvalósító fake; modellezi a tipp.ly auth-kaput."""

    def __init__(
        self,
        *,
        session_valid: bool = False,
        login_succeeds: bool = True,
        snapshot: str = "<fixtures snapshot>",
        fail_first_n_fills: int = 0,
        bot_walled: bool = False,
    ):
        self.session_valid = session_valid
        self.login_succeeds = login_succeeds
        self._snapshot = snapshot
        self.fail_first_n_fills = fail_first_n_fills
        self.bot_walled = bot_walled

        self.opened_with_storage_state: str | None = None
        self.filled: dict[str, str] = {}
        self.checkboxes: dict[str, bool] = {}
        self.clicked: list[str] = []
        self.saved_storage_state_to: str | None = None
        self.acted: list = []
        self.screenshots: list[str] = []
        self.page_values: dict[str, str] = {}
        self._fill_calls = 0
        self.snapshots_taken = 0
        self.tip_submitted = False
        self.closed = False

        self._authenticated = False
        self._url = "about:blank"

    async def open(self, storage_state: str | None = None) -> None:
        self.opened_with_storage_state = storage_state
        if storage_state is not None and self.session_valid:
            self._authenticated = True

    async def goto(self, url: str) -> None:
        if "/bets" in url and not self._authenticated:
            self._url = url.replace("/bets", "/login")
        else:
            self._url = url

    async def current_url(self) -> str:
        return self._url

    async def fill(self, selector: str, value: str) -> None:
        self.filled[selector] = value

    async def set_checkbox(self, selector: str, checked: bool) -> None:
        self.checkboxes[selector] = checked

    async def click(self, selector: str) -> None:
        self.clicked.append(selector)
        if self.login_succeeds:
            self._authenticated = True

    async def save_storage_state(self, path: str) -> None:
        self.saved_storage_state_to = path

    @staticmethod
    def _key(locator) -> str:
        return f"{locator.strategy}:{locator.value}"

    async def snapshot(self) -> str:
        self.snapshots_taken += 1
        return self._snapshot

    async def is_bot_walled(self) -> bool:
        return self.bot_walled

    async def act(self, action) -> None:
        self.acted.append(action)
        if action.kind == "fill":
            self._fill_calls += 1
            landed = "__wrong__" if self._fill_calls <= self.fail_first_n_fills else action.value
            self.page_values[self._key(action.locator)] = landed

    async def read_back(self, locator) -> str | None:
        return self.page_values.get(self._key(locator))

    async def screenshot(self, path: str) -> None:
        self.screenshots.append(path)

    async def submit(self) -> None:
        self.tip_submitted = True

    async def start_trace(self) -> None:
        pass

    async def stop_trace(self, path: str) -> None:
        pass

    async def close(self) -> None:
        self.closed = True


class FakeLlm:
    """A locate LLM-et megvalósító fake; előre megadott válaszokat ad sorban."""

    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.prompts: list[str] = []

    async def locate(self, prompt: str):
        self.prompts.append(prompt)
        return self._payloads.pop(0)
