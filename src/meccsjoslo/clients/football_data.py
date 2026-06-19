"""football-data.org v4 kliens.

Vékony réteg az API fölött: `X-Auth-Token` hitelesítés, **10 kérés/perc
rate-limit kezelés** (429 → `Retry-After` szerinti várakozás + újrapróba), és
az `odds` mező kiszűrése (a jóslás nem használhat fogadóirodai szorzót).

A `transport` és a `sleep` injektálható, így a rate-limit/retry viselkedés
valós HTTP és valós idő nélkül tesztelhető (lásd `tests/fakes.py`).
"""

from __future__ import annotations

import json
import time
from typing import Callable, NamedTuple
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from meccsjoslo import config


class Response(NamedTuple):
    status: int
    headers: dict
    json: dict


def _default_transport(url: str, headers: dict) -> Response:
    """Valós HTTP transport (urllib, stdlib)."""
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode("utf-8"))
            return Response(r.status, dict(r.headers), body)
    except HTTPError as e:  # 429 és egyéb hibakódok
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = {}
        return Response(e.code, dict(e.headers or {}), body)


class FootballDataClient:
    def __init__(
        self,
        token: str,
        base: str = config.FOOTBALL_DATA_BASE,
        transport: Callable[[str, dict], Response] = _default_transport,
        sleep: Callable[[float], None] = time.sleep,
        max_retries: int = 3,
    ) -> None:
        self._token = token
        self._base = base.rstrip("/")
        self._transport = transport
        self._sleep = sleep
        self._max_retries = max_retries

    # -- alap -------------------------------------------------------------
    def get(self, path: str, params: dict | None = None) -> dict:
        url = self._build_url(path, params)
        headers = {"X-Auth-Token": self._token}
        for attempt in range(self._max_retries + 1):
            resp = self._transport(url, headers)
            if resp.status == 429:
                if attempt < self._max_retries:
                    self._sleep(self._retry_after(resp.headers))
                    continue
                raise RuntimeError(
                    f"football-data rate limit (HTTP 429) a {self._max_retries} "
                    f"újrapróba után is: {path}"
                )
            if resp.status >= 400:
                raise RuntimeError(
                    f"football-data hiba: HTTP {resp.status} – {resp.json} ({path})"
                )
            return self._strip_odds(resp.json)
        raise AssertionError("elérhetetlen ág")

    def _build_url(self, path: str, params: dict | None) -> str:
        url = self._base + path
        if params:
            url += "?" + urlencode(params)
        return url

    # Ha a 429 nem ad Retry-After-t (football-data free tier), a perc-keret a
    # naptári perc fordulóján áll vissza → ~1 perc várakozás a biztos.
    _DEFAULT_RATELIMIT_WAIT = 61.0

    @staticmethod
    def _retry_after(headers: dict) -> float:
        raw = headers.get("Retry-After")
        if raw is not None:
            try:
                return max(float(raw), 1.0)
            except (TypeError, ValueError):
                pass
        return FootballDataClient._DEFAULT_RATELIMIT_WAIT

    @staticmethod
    def _strip_odds(obj):
        """Az `odds` kulcsot mindenhonnan eltávolítja (odds tilos)."""
        if isinstance(obj, dict):
            obj.pop("odds", None)
            for value in obj.values():
                FootballDataClient._strip_odds(value)
        elif isinstance(obj, list):
            for item in obj:
                FootballDataClient._strip_odds(item)
        return obj

    # -- kényelmi végpontok ----------------------------------------------
    def matches(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        status: str | None = None,
        stage: str | None = None,
    ) -> dict:
        params: dict[str, str] = {}
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        if status:
            params["status"] = status
        if stage:
            params["stage"] = stage
        return self.get(f"/competitions/{config.COMPETITION}/matches", params)

    def match(self, match_id: int | str) -> dict:
        return self.get(f"/matches/{match_id}")

    def head2head(self, match_id: int | str, limit: int = config.RECENT_N) -> dict:
        return self.get(f"/matches/{match_id}/head2head", {"limit": limit})

    def standings(self) -> dict:
        return self.get(f"/competitions/{config.COMPETITION}/standings")
