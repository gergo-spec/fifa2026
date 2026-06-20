"""tipp.ly folyamat – login / fill / verify / submit / guardrailek (fake browser)."""

import asyncio

from pydantic import SecretStr

from meccsjoslo.tipply.config import TipplyConfig
from meccsjoslo.tipply.fill import fill_and_verify
from meccsjoslo.tipply.login import ensure_authenticated
from meccsjoslo.tipply.state import Match, Score
from tests.fakes_tipply import FakeBrowser, FakeLlm

MATCH = Match(home="Spanyolország", away="Szaúd-Arábia")
SCORE = Score(home_goals=2, away_goals=0)


def _plan(match_id="1", hg="2", ag="0", confidence=0.9):
    return {
        "actions": [
            {"kind": "fill", "locator": {"strategy": "css", "value": f"input[name='bets[{match_id}][home_scores]']"}, "value": hg},
            {"kind": "fill", "locator": {"strategy": "css", "value": f"input[name='bets[{match_id}][away_scores]']"}, "value": ag},
        ],
        "confidence": confidence,
        "rationale": "ok",
    }


def _cfg(tmp_path):
    return TipplyConfig(email="e@x", password=SecretStr("pw"), storage_state_path=tmp_path / "s.json")


# --- login ----------------------------------------------------------------

def test_login_reuses_valid_session(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.storage_state_path.write_text("{}")  # mentett session létezik
    browser = FakeBrowser(session_valid=True)
    outcome = asyncio.run(ensure_authenticated(browser, cfg))
    assert outcome.authenticated and outcome.reused_session


def test_login_submits_form_when_no_session(tmp_path):
    browser = FakeBrowser(session_valid=False, login_succeeds=True)
    outcome = asyncio.run(ensure_authenticated(browser, _cfg(tmp_path)))
    assert outcome.authenticated and not outcome.reused_session
    assert browser.filled  # email/jelszó kitöltve
    assert browser.saved_storage_state_to is not None


# --- fill / verify / submit -----------------------------------------------

def test_fill_and_verify_fills(tmp_path):
    browser, llm = FakeBrowser(), FakeLlm([_plan()])
    report = asyncio.run(fill_and_verify(browser, llm, match=MATCH, score=SCORE))
    assert report.status == "filled"
    assert not browser.tip_submitted


def test_submit_flag_submits(tmp_path):
    browser, llm = FakeBrowser(), FakeLlm([_plan()])
    report = asyncio.run(fill_and_verify(browser, llm, match=MATCH, score=SCORE, submit=True))
    assert report.status == "submitted"
    assert browser.tip_submitted


def test_existing_tip_skipped():
    browser, llm = FakeBrowser(), FakeLlm([_plan()])
    browser.page_values["css:input[name='bets[1][home_scores]']"] = "3"
    browser.page_values["css:input[name='bets[1][away_scores]']"] = "1"
    report = asyncio.run(fill_and_verify(browser, llm, match=MATCH, score=SCORE))
    assert report.status == "skipped"


def test_bot_wall_stops():
    browser = FakeBrowser(bot_walled=True)
    report = asyncio.run(fill_and_verify(browser, FakeLlm([_plan()]), match=MATCH, score=SCORE))
    assert report.status == "needs_human" and report.reason == "bot_wall"


def test_low_confidence_aborts():
    browser, llm = FakeBrowser(), FakeLlm([_plan(confidence=0.3)])
    report = asyncio.run(fill_and_verify(browser, llm, match=MATCH, score=SCORE))
    assert report.status == "needs_human" and report.reason == "low_confidence"


def test_no_match_aborts():
    empty = {"actions": [], "confidence": 0.0, "rationale": "no fixture"}
    report = asyncio.run(fill_and_verify(FakeBrowser(), FakeLlm([empty]), match=MATCH, score=SCORE))
    assert report.status == "needs_human" and report.reason == "no_match"
