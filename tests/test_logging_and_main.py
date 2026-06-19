"""Story 010 – CSV-naplózás + napi entrypoint (run_once)."""

import csv
from datetime import datetime, timezone

from meccsjoslo import config
from meccsjoslo.clients.football_data import FootballDataClient
from meccsjoslo.graph import default_graph
from meccsjoslo.logging_csv import COLUMNS, append_prediction
from meccsjoslo.main import run_once
from tests.fakes import FakeFootballDataSite

VENUES = config.PROJECT_ROOT / "tests" / "fixtures" / "venues.json"

GOOD = {
    "prob_home": 0.6, "prob_draw": 0.25, "prob_away": 0.15,
    "expected_goals_home": 1.8, "expected_goals_away": 0.7,
    "rationale": "Teszt indoklás, vesszővel.",
}


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_append_writes_header_once_with_stable_columns(tmp_path):
    p = tmp_path / "out.csv"
    state = {"match_id": 1, "home_tla": "ECU", "prob_home": 0.6, "rationale": "ok"}
    append_prediction(state, p, run_date="2026-06-19")
    append_prediction({"match_id": 2, "home_tla": "TUN"}, p, run_date="2026-06-19")
    text = p.read_text(encoding="utf-8")
    assert text.count(",".join(COLUMNS)) == 1  # fejléc pontosan egyszer
    rows = _read(p)
    assert len(rows) == 2
    assert rows[0]["match_id"] == "1"
    assert list(rows[0].keys()) == COLUMNS


def test_decimal_point_and_quoted_rationale(tmp_path):
    p = tmp_path / "out.csv"
    append_prediction(
        {"match_id": 7, "prob_home": 0.6667, "rationale": "a, b, c"},
        p,
        run_date="2026-06-19",
    )
    raw = p.read_text(encoding="utf-8")
    assert "0.6667" in raw  # tizedes pont
    assert '"a, b, c"' in raw  # vesszős rationale idézőjelben
    assert _read(p)[0]["rationale"] == "a, b, c"


def _client():
    # magas limit: az integrációs teszt sok hívást indít, a rate-limitet külön
    # teszt fedi (test_football_data_client.py)
    site = FakeFootballDataSite(limit=10_000)
    return FootballDataClient(token="t", transport=site.transport())


def _graph(client):
    return default_graph(
        client,
        predictor=lambda prompt: dict(GOOD),
        ranking_file=config.RANKING_FILE,
        venues_file=VENUES,
    )


def test_run_once_filters_to_48h_window(tmp_path):
    client = _client()
    csv_path = tmp_path / "predictions.csv"
    sleeps = []
    now = datetime(2026, 6, 21, 5, 0, tzinfo=timezone.utc)  # 05:00Z
    count = run_once(
        client, _graph(client), csv_path=csv_path, now=now, sleep=sleeps.append
    )
    # a 00:00 és 04:00 meccs now előtt → kihagyva; marad a 16:00 és 19:00
    assert count == 2
    rows = _read(csv_path)
    assert {r["home_tla"] for r in rows} == {"ESP", "BEL"}
    assert all(r["run_date"] == now.date().isoformat() for r in rows)
    assert sleeps  # rate-limit szünet meghívódott


def test_run_once_full_window_predicts_all_four(tmp_path):
    client = _client()
    csv_path = tmp_path / "p.csv"
    now = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)
    count = run_once(client, _graph(client), csv_path=csv_path, now=now, sleep=lambda s: None)
    assert count == 4
    rows = _read(csv_path)
    assert len(rows) == 4
    # a venue/állás-függő ágak is lefutottak: van érvényes valószínűség
    assert all(abs(sum(float(r[k]) for k in ("prob_home", "prob_draw", "prob_away")) - 1.0) < 1e-6 for r in rows)
