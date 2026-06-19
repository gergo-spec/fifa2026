"""Story 009 – predict node (Gemini, strukturált kimenet)."""

import pytest

from meccsjoslo.nodes.predict import build_prompt, make_predict


def base_state(**extra):
    state = {
        "home_name": "Ecuador", "away_name": "Curaçao",
        "home_tla": "ECU", "away_tla": "CUW",
        "stage": "GROUP_STAGE", "group": "GROUP_E",
        "home_rank": 23, "away_rank": 82, "rank_diff": 59,
        "home_form": {"weighted": 1.0, "win_rate": 1.0, "sample_size": 2, "insufficient": False},
        "away_form": {"weighted": 0.11, "win_rate": 0.0, "sample_size": 2, "insufficient": False},
        "home_goals": {"attack": 2.5, "defense": 0.5},
        "away_goals": {"attack": 0.5, "defense": 1.5},
        "home_fatigue": {"rest_days": 4, "matches_in_window": 2},
        "away_fatigue": {"rest_days": 4, "matches_in_window": 2},
        "host_advantage": "none",
        "venue_altitude_m": 2240, "venue_climate": "high-altitude",
    }
    state.update(extra)
    return state


GOOD = {
    "prob_home": 0.7, "prob_draw": 0.2, "prob_away": 0.1,
    "expected_goals_home": 2.3, "expected_goals_away": 0.6,
    "rationale": "Ecuador jobb ranglistán és formában.",
}


def test_returns_three_probabilities_and_xg():
    out = make_predict(lambda prompt: dict(GOOD))(base_state())
    assert out["prob_home"] == 0.7
    assert out["prob_draw"] == 0.2
    assert out["prob_away"] == 0.1
    assert out["expected_goals_home"] == 2.3
    assert out["rationale"].startswith("Ecuador")


def test_probabilities_are_normalized_to_sum_one():
    raw = dict(GOOD, prob_home=0.5, prob_draw=0.4, prob_away=0.3)  # összeg 1.2
    out = make_predict(lambda prompt: raw)(base_state())
    assert out["prob_home"] + out["prob_draw"] + out["prob_away"] == pytest.approx(1.0)
    assert out["prob_home"] == pytest.approx(0.5 / 1.2, abs=1e-4)


def test_group_stage_raw_standings_in_prompt():
    standings = {
        "group": "GROUP_E",
        "home_row": {"position": 1, "points": 6, "goalDifference": 4},
        "away_row": {"position": 4, "points": 1, "goalDifference": -2},
        "table": [],
    }
    prompt = build_prompt(base_state(group_standings=standings))
    assert "GROUP_E" in prompt
    assert "6" in prompt and "Csoportállás" in prompt


def test_prompt_never_contains_odds():
    prompt = build_prompt(base_state())
    assert "odds" not in prompt.lower()
    assert "szorz" not in prompt.lower()


def test_invalid_then_valid_triggers_one_retry():
    calls = []

    def flaky(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            return {"garbage": True}  # érvénytelen első válasz
        return dict(GOOD)

    out = make_predict(flaky)(base_state())
    assert len(calls) == 2  # pontosan egy újrapróba
    assert out["prob_home"] == 0.7


def test_persistently_invalid_raises():
    with pytest.raises(RuntimeError, match="érvényes"):
        make_predict(lambda prompt: {"nope": 1})(base_state())


def test_zero_sum_probs_are_invalid_and_raise():
    bad = dict(GOOD, prob_home=0, prob_draw=0, prob_away=0)
    with pytest.raises(RuntimeError):
        make_predict(lambda prompt: bad)(base_state())
