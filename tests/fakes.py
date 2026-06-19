"""Mockolt football-data.org „site" tesztekhez.

A valós HTTP helyett ez szolgálja ki a `tests/fixtures/football_data/`
fixture-öket, és **szimulálja a 10 kérés/perc rate limitet**: ha az ablakon
belül elfogy a keret, 429-et ad `Retry-After` + `X-Requests-Available-Minute: 0`
fejlécekkel — pont, ahogy a valós API. Így a kliens (Story 002) várakozó/retry
logikája determinisztikusan tesztelhető egy `ManualClock`-kal.

Használat tesztben:

    site = FakeFootballDataSite()                 # valós idő
    resp = site.request("/competitions/WC/matches",
                        {"dateFrom": "2026-06-21", "dateTo": "2026-06-23"})
    assert resp.status == 200
    assert resp.json["count"] == 4

Rate limit determinisztikusan:

    clock = ManualClock()
    site = FakeFootballDataSite(clock=clock, limit=10, window_s=60)
    for _ in range(10):
        assert site.request("/competitions/WC/standings").status == 200
    assert site.request("/competitions/WC/standings").status == 429   # keret elfogyott
    clock.advance(60)
    assert site.request("/competitions/WC/standings").status == 200   # ablak továbblépett
"""

from __future__ import annotations

import json
import math
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "football_data"


@dataclass
class Response:
    """Egy API-válasz: státusz, fejlécek, parse-olt JSON body."""

    status: int
    headers: dict[str, str]
    json: dict


class ManualClock:
    """Kézzel léptethető óra a rate-limit determinisztikus teszteléséhez."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = float(start)

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += float(seconds)


class _RealClock:
    def now(self) -> float:
        return time.monotonic()


class FakeFootballDataSite:
    """football-data v4 fixture-kiszolgáló + rate-limit szimuláció.

    - `limit` kérés engedélyezett `window_s` másodperces csúszóablakban.
    - A limit túllépése 429-et ad (a rate-limitelt kérés NEM számít bele a
      keretbe).
    - Minden kiszolgált kéréshez `X-Requests-Available-Minute` fejléc tartozik.
    - Az `odds` mezőt a fixture-ök tartalmazzák (a valós kliens dolga kiszűrni);
      itt szándékosan benne hagyjuk, hogy a kliens szűrése tesztelhető legyen.
    """

    def __init__(
        self,
        fixtures_dir: Path | str = FIXTURES_DIR,
        clock: ManualClock | _RealClock | None = None,
        limit: int = 10,
        window_s: float = 60.0,
    ) -> None:
        self._dir = Path(fixtures_dir)
        self._clock = clock or _RealClock()
        self._limit = limit
        self._window = window_s
        self._req_times: deque[float] = deque()
        self._cache: dict[str, dict] = {}
        # A kiszolgált (200-as) kérések naplója assertekhez: (path, params).
        self.calls: list[tuple[str, dict]] = []

    # -- fixture betöltés -------------------------------------------------
    def _load(self, name: str) -> dict:
        if name not in self._cache:
            self._cache[name] = json.loads(
                (self._dir / name).read_text(encoding="utf-8")
            )
        return self._cache[name]

    # -- rate limit -------------------------------------------------------
    def _purge_old(self, now: float) -> None:
        while self._req_times and now - self._req_times[0] >= self._window:
            self._req_times.popleft()

    def _rate_limited_response(self, now: float) -> Response:
        retry_after = math.ceil(self._window - (now - self._req_times[0]))
        return Response(
            status=429,
            headers={
                "X-Requests-Available-Minute": "0",
                "Retry-After": str(max(retry_after, 1)),
            },
            json=self._load("rate_limit_429.json"),
        )

    # -- routing ----------------------------------------------------------
    def request(self, path: str, params: dict | None = None) -> Response:
        """Egy API-kérés kiszolgálása (valós HTTP helyett)."""
        params = params or {}
        now = self._clock.now()
        self._purge_old(now)
        if len(self._req_times) >= self._limit:
            return self._rate_limited_response(now)

        body = self._route(path, params)
        self._req_times.append(now)
        self.calls.append((self._normalize(path), dict(params)))
        remaining = self._limit - len(self._req_times)
        return Response(
            status=200,
            headers={"X-Requests-Available-Minute": str(remaining)},
            json=body,
        )

    def transport(self):
        """URL-alapú transport-callable a valódi klienshez.

        A `FootballDataClient` teljes URL-lel és fejlécekkel hív; ez az adapter
        visszabontja path+query-re és a `request()`-re továbbítja, így a kliens
        rate-limit/retry logikája a fake ellen tesztelhető.
        """

        def _call(url: str, headers: dict) -> Response:
            parsed = urlparse(url)
            params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            return self.request(parsed.path, params)

        return _call

    @staticmethod
    def _normalize(path: str) -> str:
        p = urlparse(path).path if "://" in path else path
        # a /v4 prefixet (ha van) levágjuk
        if p.startswith("/v4"):
            p = p[len("/v4"):]
        return p.rstrip("/")

    def _route(self, path: str, params: dict) -> dict:
        p = self._normalize(path)
        parts = [seg for seg in p.split("/") if seg]

        if p == "/competitions/WC/standings":
            return self._load("standings.json")

        if p == "/competitions/WC/matches":
            if str(params.get("status", "")).upper() == "FINISHED":
                return self._load("matches_finished.json")
            return self._load("matches_upcoming.json")

        # /matches/{id}[/head2head]
        if len(parts) >= 2 and parts[0] == "matches":
            match_id = parts[1]
            if len(parts) >= 3 and parts[2] == "head2head":
                data = self._load("head2head.json").get(match_id)
                if data is None:
                    raise KeyError(f"nincs head2head fixture: {match_id}")
                return data
            data = self._load("match_details.json").get(match_id)
            if data is None:
                raise KeyError(f"nincs match-detail fixture: {match_id}")
            return data

        raise KeyError(f"a fake site nem ismeri ezt az utat: {p}")


def _smoke() -> None:
    """Önteszt: `uv run python tests/fakes.py` – validálja a fixture-öket."""
    site = FakeFootballDataSite()
    up = site.request(
        "/competitions/WC/matches",
        {"dateFrom": "2026-06-21", "dateTo": "2026-06-23"},
    )
    assert up.status == 200 and up.json["count"] == 4, up.json
    det = site.request("/matches/537401")
    assert det.json["venue"] == "Estadio Azteca", det.json
    h2h = site.request("/matches/537402/head2head", {"limit": 5})
    assert h2h.json["aggregates"]["numberOfMatches"] == 3, h2h.json
    fin = site.request("/competitions/WC/matches", {"status": "FINISHED"})
    assert fin.json["count"] == 16, fin.json
    st = site.request("/competitions/WC/standings")
    assert len(st.json["standings"]) == 4, st.json

    # rate limit
    clock = ManualClock()
    rl = FakeFootballDataSite(clock=clock, limit=10, window_s=60)
    for _ in range(10):
        assert rl.request("/competitions/WC/standings").status == 200
    blocked = rl.request("/competitions/WC/standings")
    assert blocked.status == 429 and blocked.headers["X-Requests-Available-Minute"] == "0"
    clock.advance(60)
    assert rl.request("/competitions/WC/standings").status == 200
    print("OK – minden fixture betölt és a rate-limit mock működik.")


if __name__ == "__main__":
    _smoke()
