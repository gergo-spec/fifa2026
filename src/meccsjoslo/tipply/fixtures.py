"""Determinisztikus guard: a megtalált fixture tényleg a kért meccs-e.

Az LLM ráerőltethet egy fixture-t, ami csak az egyik csapatra illik. A
read-back csak az *érték* beírását igazolja, nem azt, hogy a *jó* meccset
választottuk – ezért itt a választott fixture csapatneveit a kéréshez mérjük,
mielőtt bármit kitöltenénk.
"""

from __future__ import annotations

import json
import re
import unicodedata

_ID_RE = re.compile(r"bets\[(\d+)\]")


def _normalize(name: str | None) -> str:
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return "".join(c for c in stripped.casefold() if c.isalnum())


def _names_match(requested: str, actual: str | None) -> bool:
    a, b = _normalize(requested), _normalize(actual)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def _parse_fixtures(snapshot: str) -> list[dict]:
    try:
        return json.loads(snapshot).get("fixtures", []) or []
    except (ValueError, AttributeError):
        return []


def _chosen_ids(plan) -> set[str]:
    ids = set()
    for action in plan.actions:
        if action.kind != "fill":
            continue
        m = _ID_RE.search(action.locator.value or "")
        if m:
            ids.add(m.group(1))
    return ids


def located_fixture_matches(snapshot: str, match, plan) -> bool:
    """Csak *biztos* eltérésnél ad False-t; True, ha nem dönthető el.

    A nem ellenőrizhető esetek (nem-fixtures snapshot, kétértelmű/hiányzó id,
    hiányzó nevek) True-t adnak, hogy a guard sose blokkoljon egy jogosan fuzzy
    egyezést – csak a nyilvánvalóan rossz fixture-t állítja meg.
    """
    fixtures = _parse_fixtures(snapshot)
    if not fixtures:
        return True

    ids = _chosen_ids(plan)
    if len(ids) != 1:
        return True
    chosen = next(iter(ids))

    fixture = next(
        (f for f in fixtures if _ID_RE.search(f.get("home_input", "") or "") and
         _ID_RE.search(f["home_input"]).group(1) == chosen),
        None,
    )
    if fixture is None or not fixture.get("home") or not fixture.get("away"):
        return True

    return _names_match(match.home, fixture["home"]) and _names_match(match.away, fixture["away"])
