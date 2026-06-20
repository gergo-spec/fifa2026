"""ntfy.sh értesítések (programindulás + meccsenkénti tipp).

Egyszerű HTTP POST a `https://ntfy.sh/<topic>`-ra (alapból a
`gergo_vb2026_tippek` topic). Best-effort: ha az értesítés hibázik, a futást
SOSEM töri meg. A `transport` injektálható, így hálózat nélkül tesztelhető.
"""

from __future__ import annotations

import urllib.request
from typing import Callable

from meccsjoslo.tipply.state import Score

_STATUS_HU = {
    "submitted": "✅ mentve",
    "filled": "📝 beírva (dry-run, nem mentve)",
    "skipped": "⏭️ kihagyva (már volt tipp)",
    "needs_human": "⚠️ kézi beavatkozás kell",
    "no_match": "❓ nincs meccs",
}


def _http_post(endpoint: str, data: bytes, headers: dict) -> int:
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status


class Notifier:
    def __init__(self, url: str, topic: str, transport: Callable | None = None):
        self.endpoint = f"{url.rstrip('/')}/{topic}"
        self._transport = transport or _http_post

    def send(self, body: str, *, title: str | None = None, tags: str | None = None) -> bool:
        """Egy értesítés küldése. Hibát nem dob – best-effort."""
        headers = {"Content-Type": "text/plain; charset=utf-8"}
        if title:
            headers["Title"] = title  # ASCII ajánlott
        if tags:
            headers["Tags"] = tags
        try:
            self._transport(self.endpoint, body.encode("utf-8"), headers)
            return True
        except Exception as err:  # az értesítés sose törje meg a futást
            print(f"[ntfy] értesítés sikertelen: {type(err).__name__}: {err}")
            return False


def make_notifier(cfg: dict[str, str] | None = None, *, transport: Callable | None = None):
    """Notifier a `.env`-ből, vagy `None` ha kikapcsolt (`NTFY_ENABLE=0`).

    Alapból BE van kapcsolva, a `gergo_vb2026_tippek` topicra.
    """
    from meccsjoslo import config

    cfg = cfg if cfg is not None else config.load_env()
    if not config.ntfy_enabled(cfg):
        return None
    return Notifier(config.ntfy_url(cfg), config.ntfy_topic(cfg), transport=transport)


def notify_started(notifier: Notifier | None, context: str = "") -> None:
    if notifier is None:
        return
    suffix = f" — {context}" if context else ""
    notifier.send(f"🚀 A meccsjósló elindult{suffix}", title="VB2026 tippek", tags="rocket")


def notify_tip(notifier: Notifier | None, home: str, away: str, score: Score, status: str) -> None:
    if notifier is None:
        return
    label = _STATUS_HU.get(status, status)
    body = f"{home} {score.home_goals}:{score.away_goals} {away} — {label}"
    notifier.send(body, title="VB2026 tipp", tags="soccer")
