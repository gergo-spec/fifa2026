"""A tesztadat (fixture-ök) és a mockolt football-data site validálása.

Ez a teszt magát a tesztadatot ellenőrzi (nem az alkalmazás-kódot, ami még
nincs). Garantálja, hogy a fixture-ök konzisztensek és a rate-limit mock a
10 kérés/perc szabály szerint viselkedik.
"""

import pytest

from tests.fakes import FakeFootballDataSite, ManualClock

UPCOMING = {
    537401: ("ECU", "CUW", "GROUP_E", "2026-06-21T00:00:00Z"),
    537402: ("TUN", "JPN", "GROUP_F", "2026-06-21T04:00:00Z"),
    537403: ("ESP", "KSA", "GROUP_H", "2026-06-21T16:00:00Z"),
    537404: ("BEL", "IRN", "GROUP_G", "2026-06-21T19:00:00Z"),
}


def test_upcoming_matches_match_the_image(fake_site: FakeFootballDataSite):
    data = fake_site.request(
        "/competitions/WC/matches",
        {"dateFrom": "2026-06-21", "dateTo": "2026-06-23"},
    ).json
    assert data["count"] == 4
    got = {
        m["id"]: (m["homeTeam"]["tla"], m["awayTeam"]["tla"], m["group"], m["utcDate"])
        for m in data["matches"]
    }
    assert got == UPCOMING
    assert all(m["status"] == "SCHEDULED" for m in data["matches"])
    assert all(m["stage"] == "GROUP_STAGE" for m in data["matches"])


@pytest.mark.parametrize("match_id, venue", [
    (537401, "Estadio Azteca"),
    (537402, "Hard Rock Stadium"),
    (537403, "MetLife Stadium"),
    (537404, "BMO Field"),
])
def test_match_detail_has_venue(fake_site, match_id, venue):
    assert fake_site.request(f"/matches/{match_id}").json["venue"] == venue


def test_finished_matches_give_two_games_per_team(fake_site):
    matches = fake_site.request(
        "/competitions/WC/matches", {"status": "FINISHED"}
    ).json["matches"]
    assert len(matches) == 16
    played: dict[str, int] = {}
    for m in matches:
        assert m["status"] == "FINISHED"
        for side in ("homeTeam", "awayTeam"):
            played[m[side]["tla"]] = played.get(m[side]["tla"], 0) + 1
    # mind a 8 érintett csapat pontosan 2 lejátszott meccs
    for tla in ("ECU", "CUW", "TUN", "JPN", "ESP", "KSA", "BEL", "IRN"):
        assert played[tla] == 2, tla


def test_standings_have_four_groups_each_with_four_teams(fake_site):
    standings = fake_site.request("/competitions/WC/standings").json["standings"]
    groups = {s["group"]: s["table"] for s in standings}
    assert set(groups) == {"GROUP_E", "GROUP_F", "GROUP_G", "GROUP_H"}
    for table in groups.values():
        assert len(table) == 4
        # pontszám szerint nem-növekvő (rendezett tabella)
        pts = [row["points"] for row in table]
        assert pts == sorted(pts, reverse=True)


def test_head2head_present_for_each_upcoming(fake_site):
    for match_id in UPCOMING:
        agg = fake_site.request(f"/matches/{match_id}/head2head").json["aggregates"]
        assert agg["numberOfMatches"] >= 1


def test_finished_matches_carry_no_inconsistent_scores(fake_site):
    for m in fake_site.request(
        "/competitions/WC/matches", {"status": "FINISHED"}
    ).json["matches"]:
        ft = m["score"]["fullTime"]
        winner = m["score"]["winner"]
        if ft["home"] > ft["away"]:
            assert winner == "HOME_TEAM"
        elif ft["home"] < ft["away"]:
            assert winner == "AWAY_TEAM"
        else:
            assert winner == "DRAW"


def test_rate_limit_blocks_after_ten_requests_per_window():
    clock = ManualClock()
    site = FakeFootballDataSite(clock=clock, limit=10, window_s=60)
    for _ in range(10):
        assert site.request("/competitions/WC/standings").status == 200
    blocked = site.request("/competitions/WC/standings")
    assert blocked.status == 429
    assert blocked.headers["X-Requests-Available-Minute"] == "0"
    assert int(blocked.headers["Retry-After"]) > 0


def test_rate_limit_recovers_after_window_slides():
    clock = ManualClock()
    site = FakeFootballDataSite(clock=clock, limit=10, window_s=60)
    for _ in range(10):
        site.request("/competitions/WC/standings")
    assert site.request("/competitions/WC/standings").status == 429
    clock.advance(60)
    assert site.request("/competitions/WC/standings").status == 200


def test_available_minute_header_counts_down(fake_site_clocked):
    first = fake_site_clocked.request("/competitions/WC/standings")
    assert first.headers["X-Requests-Available-Minute"] == "9"
    second = fake_site_clocked.request("/competitions/WC/standings")
    assert second.headers["X-Requests-Available-Minute"] == "8"


def test_fixtures_still_contain_odds_for_client_to_strip(fake_site):
    # a fixture szándékosan tartalmaz odds-ot; a valós kliens feladata kiszűrni
    m = fake_site.request(
        "/competitions/WC/matches",
        {"dateFrom": "2026-06-21", "dateTo": "2026-06-23"},
    ).json["matches"][0]
    assert "odds" in m
