"""Story 002 – football-data.org v4 kliens."""

import pytest

from meccsjoslo.clients.football_data import FootballDataClient
from tests.fakes import FakeFootballDataSite, ManualClock, Response


def make_client(site, **kw):
    return FootballDataClient(token="tok", transport=site.transport(), **kw)


def test_get_sends_auth_token_header():
    seen = {}

    def transport(url, headers):
        seen["url"] = url
        seen["headers"] = headers
        return Response(200, {}, {"ok": True})

    client = FootballDataClient(token="my-secret", transport=transport)
    client.get("/competitions/WC/standings")
    assert seen["headers"]["X-Auth-Token"] == "my-secret"
    assert seen["url"].startswith("https://api.football-data.org/v4")


def test_matches_builds_query_and_returns_payload():
    site = FakeFootballDataSite()
    data = make_client(site).matches(date_from="2026-06-21", date_to="2026-06-23")
    assert data["count"] == 4
    path, params = site.calls[-1]
    assert path == "/competitions/WC/matches"
    assert params == {"dateFrom": "2026-06-21", "dateTo": "2026-06-23"}


def test_matches_finished_filter():
    site = FakeFootballDataSite()
    data = make_client(site).matches(status="FINISHED")
    assert data["count"] == 16
    assert site.calls[-1][1] == {"status": "FINISHED"}


def test_odds_stripped_from_matches():
    site = FakeFootballDataSite()
    data = make_client(site).matches(date_from="2026-06-21", date_to="2026-06-23")
    assert all("odds" not in m for m in data["matches"])


def test_odds_stripped_from_match_detail():
    site = FakeFootballDataSite()
    detail = make_client(site).match(537401)
    assert "odds" not in detail
    assert detail["venue"] == "Estadio Azteca"


def test_head2head_passes_limit():
    site = FakeFootballDataSite()
    data = make_client(site).head2head(537402, limit=5)
    assert data["aggregates"]["numberOfMatches"] == 3
    assert site.calls[-1] == ("/matches/537402/head2head", {"limit": "5"})


def test_429_then_retry_after_waiting():
    clock = ManualClock()
    site = FakeFootballDataSite(clock=clock, limit=10, window_s=60)
    # a kliens sleep-je előretekeri az órát → az ablak csúszik, a retry sikerül
    client = make_client(site, sleep=clock.advance, max_retries=3)

    # merítsük ki a keretet 10 hívással
    for _ in range(10):
        client.standings()
    # a 11. hívás 429-et kapna, de a kliens megvárja a Retry-After-t és újrapróbál
    data = client.standings()
    assert data["standings"]  # sikeres válasz a várakozás után


def test_429_gives_up_after_max_retries():
    clock = ManualClock()
    site = FakeFootballDataSite(clock=clock, limit=10, window_s=60)
    # a sleep NEM tekeri az órát → a keret sosem szabadul fel → kivétel
    client = make_client(site, sleep=lambda s: None, max_retries=2)
    for _ in range(10):
        client.standings()
    with pytest.raises(RuntimeError, match="429"):
        client.standings()


def test_standings_and_match_paths():
    site = FakeFootballDataSite()
    client = make_client(site)
    assert len(client.standings()["standings"]) == 4
    assert client.match(537403)["group"] == "GROUP_H"
