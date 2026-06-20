"""tipp.ly fixture-guard – magyar nevek egyeztetése a választott fixture-rel."""

import json

from meccsjoslo.tipply.fixtures import located_fixture_matches
from meccsjoslo.tipply.state import Action, Locator, LocatePlan, Match


def _snapshot():
    return json.dumps(
        {
            "fixtures": [
                {"home": "Spanyolország", "away": "Szaúd-Arábia",
                 "home_input": "bets[7][home_scores]", "away_input": "bets[7][away_scores]"},
                {"home": "Belgium", "away": "Irán",
                 "home_input": "bets[9][home_scores]", "away_input": "bets[9][away_scores]"},
            ]
        },
        ensure_ascii=False,
    )


def _plan(match_id: str):
    return LocatePlan(
        actions=[
            Action(kind="fill", locator=Locator(strategy="css", value=f"input[name='bets[{match_id}][home_scores]']"), value="2"),
            Action(kind="fill", locator=Locator(strategy="css", value=f"input[name='bets[{match_id}][away_scores]']"), value="0"),
        ],
        confidence=0.9,
    )


def test_guard_accepts_matching_hungarian_names():
    match = Match(home="Spanyolország", away="Szaúd-Arábia")
    assert located_fixture_matches(_snapshot(), match, _plan("7")) is True


def test_guard_rejects_wrong_fixture():
    # a 9-es fixture Belgium–Irán, de a kérés Spanyolország–Szaúd → biztos eltérés
    match = Match(home="Spanyolország", away="Szaúd-Arábia")
    assert located_fixture_matches(_snapshot(), match, _plan("9")) is False


def test_guard_passes_when_snapshot_not_fixtures():
    match = Match(home="X", away="Y")
    assert located_fixture_matches("<aria tree>", match, _plan("7")) is True
