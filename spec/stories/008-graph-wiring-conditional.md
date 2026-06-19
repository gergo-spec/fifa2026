# Story 008 — Gráf összeállítás + feltételes elágazás

## Cél
A LangGraph `StateGraph` összekötése a SPECIFICATION 5. szakasza szerint.

## Indoklás
A feltételes ág (csoportkör ↔ kieséses) miatt kell LangGraph, nem sima lánc.

## Hatókör
- `state.py`: a közös `State` TypedDict (SPECIFICATION 3.).
- `graph.py`: `build_graph()`:
  - `START → get_rankings`, `START → get_previous_matches` (párhuzamos).
  - mindkettő → `derive_features` (fan-in).
  - `derive_features →` feltételes:
    - `GROUP_STAGE` → `get_group_standings → predict`
    - egyébként → `predict`
  - `predict → END`.
- A node-ok injektálható függőségekkel (client, config) — teszthez mockolható.

## Elfogadási kritériumok
- [ ] Csoportköri meccs → a `get_group_standings` lefut a predict előtt.
- [ ] Kieséses meccs → `get_group_standings` KIMARAD.
- [ ] `derive_features` csak akkor fut, ha mindkét nyersadat-ág kész (fan-in).
- [ ] A teljes gráf végigfut mockolt node-okkal, a State minden várt kulcsa kitöltve.

## Teszt-ötletek
- Két végigfuttatás (group / knockout) mockolt node-okkal → meglátogatott node-ok ellenőrzése.
