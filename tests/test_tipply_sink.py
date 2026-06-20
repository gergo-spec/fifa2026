"""tipp.ly sink – result→Match/Score leképezés, kerekítés, kapuzás."""

from meccsjoslo.tipply.sink import make_tipply_sink
from meccsjoslo.tipply.state import FillReport

ENABLED = {"TIPPLY_PUBLISH": "1", "TIPPLY_EMAIL": "e@x", "TIPPLY_PASSWORD": "pw"}
NAMES = {"ESP": "Spanyolország", "KSA": "Szaúd-Arábia"}


def _result(**over):
    base = {
        "home_tla": "ESP", "away_tla": "KSA",
        "home_name": "Spain", "away_name": "Saudi Arabia",
        "expected_goals_home": 2.4, "expected_goals_away": 0.5,
    }
    base.update(over)
    return base


def test_sink_maps_names_and_rounds_goals():
    calls = []

    def fake_publish(tcfg, match, score, submit):
        calls.append((match, score, submit))
        return FillReport(status="filled")

    sink = make_tipply_sink(
        ENABLED, publish=fake_publish, sleep=lambda s: None, team_names=NAMES
    )
    sink(_result())

    assert len(calls) == 1
    match, score, submit = calls[0]
    assert match.home == "Spanyolország" and match.away == "Szaúd-Arábia"
    assert (score.home_goals, score.away_goals) == (2, 0)  # round(2.4)=2, round(0.5)=0
    assert submit is False


def test_sink_submit_flag_passed_through():
    calls = []
    cfg = dict(ENABLED, TIPPLY_SUBMIT="1")
    sink = make_tipply_sink(
        cfg,
        publish=lambda *a: (calls.append(a) or FillReport(status="submitted")),
        sleep=lambda s: None,
        team_names=NAMES,
    )
    sink(_result())
    assert calls[0][3] is True  # submit=True


def test_sink_falls_back_to_english_name_when_tla_missing():
    calls = []
    sink = make_tipply_sink(
        ENABLED,
        publish=lambda *a: (calls.append(a) or FillReport(status="filled")),
        sleep=lambda s: None,
        team_names={},  # nincs térkép → home_name fallback
    )
    sink(_result())
    assert calls[0][1].home == "Spain"


def test_sink_none_when_publish_disabled():
    assert make_tipply_sink({**ENABLED, "TIPPLY_PUBLISH": "0"}) is None


def test_sink_none_when_no_credentials():
    assert make_tipply_sink({"TIPPLY_PUBLISH": "1"}) is None
