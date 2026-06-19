"""Story 005 – derive_features: forma, fáradtság, gólok."""

from meccsjoslo.nodes.derive_features import make_derive_features


def _m(date, result, gf, ga):
    return {
        "utcDate": date,
        "side": "HOME",
        "opponent_tla": "XXX",
        "goals_for": gf,
        "goals_against": ga,
        "result": result,
    }


def _state(home, away, utc="2026-06-21T00:00:00Z"):
    return {
        "utc_date": utc,
        "home_recent_matches": home,
        "away_recent_matches": away,
    }


def test_weighted_form_recent_weighted_higher():
    # frissebb elöl: [W, L]; súlyok [2,1] → (2*3 + 1*0)/(3*3) = 6/9
    home = [_m("2026-06-17T18:00:00Z", "W", 3, 1), _m("2026-06-12T18:00:00Z", "L", 0, 2)]
    out = make_derive_features()(_state(home, []))
    assert out["home_form"]["weighted"] == round(6 / 9, 4)
    assert out["home_form"]["win_rate"] == 0.5
    assert out["home_form"]["sample_size"] == 2


def test_all_wins_form_is_one():
    home = [_m("2026-06-17T18:00:00Z", "W", 3, 1), _m("2026-06-12T18:00:00Z", "W", 2, 0)]
    out = make_derive_features()(_state(home, []))
    assert out["home_form"]["weighted"] == 1.0
    assert out["home_form"]["win_rate"] == 1.0


def test_goal_averages():
    home = [_m("2026-06-17T18:00:00Z", "W", 3, 1), _m("2026-06-12T18:00:00Z", "W", 2, 0)]
    out = make_derive_features()(_state(home, []))
    assert out["home_goals"]["attack"] == 2.5
    assert out["home_goals"]["defense"] == 0.5


def test_fatigue_rest_days_and_window():
    home = [_m("2026-06-17T18:00:00Z", "W", 3, 1), _m("2026-06-12T18:00:00Z", "W", 2, 0)]
    out = make_derive_features(window_days=14)(_state(home, []))
    assert out["home_fatigue"]["rest_days"] == 3  # 06-21 00:00 − 06-17 18:00 → 3 nap
    assert out["home_fatigue"]["matches_in_window"] == 2


def test_window_excludes_old_matches():
    home = [_m("2026-06-20T18:00:00Z", "W", 1, 0), _m("2026-05-01T18:00:00Z", "L", 0, 1)]
    out = make_derive_features(window_days=14)(_state(home, []))
    assert out["home_fatigue"]["matches_in_window"] == 1  # csak a 06-20-i van az ablakban


def test_empty_history_marks_insufficient_without_error():
    out = make_derive_features()(_state([], []))
    assert out["home_form"]["insufficient"] is True
    assert out["home_form"]["sample_size"] == 0
    assert out["home_goals"]["attack"] is None
    assert out["home_fatigue"]["rest_days"] is None


def test_single_match_is_insufficient():
    home = [_m("2026-06-17T18:00:00Z", "W", 3, 1)]
    out = make_derive_features()(_state(home, []))
    assert out["home_form"]["insufficient"] is True
    assert out["home_form"]["sample_size"] == 1
