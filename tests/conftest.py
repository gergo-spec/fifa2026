"""Közös pytest fixture-ök."""

import pytest

from tests.fakes import FakeFootballDataSite, ManualClock


@pytest.fixture
def manual_clock() -> ManualClock:
    return ManualClock()


@pytest.fixture
def fake_site() -> FakeFootballDataSite:
    """Valós idejű fake football-data site (rate limit éles küszöbökkel)."""
    return FakeFootballDataSite()


@pytest.fixture
def fake_site_clocked(manual_clock: ManualClock) -> FakeFootballDataSite:
    """Determinisztikus órájú fake site rate-limit teszteléshez."""
    return FakeFootballDataSite(clock=manual_clock, limit=10, window_s=60)
