# Story 003 — `get_rankings` node

## Cél
A helyi FIFA-ranglista JSON-ból a két csapat helyezése, pontja és a
helyezéskülönbség a State-be.

## Indoklás
Csapaterő kizárólag a FIFA-ranglistából (nincs Elo). A helyezéskülönbség
önálló, hasznos feature.

## Hatókör
- `nodes/get_rankings.py`: bemenet `home_tla`, `away_tla`.
- Beolvassa `data/fifa_ranking_2026-06-11.json`-t (cache-elve, egyszer).
- State-be: `home_rank`, `away_rank`, `home_points`, `away_points`,
  `rank_diff = away_rank - home_rank`.
- Hiányzó tla → `home_rank=None` + jelzés (pl. `rankings_note`), nem 0.

## Elfogadási kritériumok
- [ ] ARG vs FRA → `home_rank=1`, `away_rank=3`, `rank_diff=2`.
- [ ] Pozitív `rank_diff` = hazai erősebb.
- [ ] Ismeretlen tla → `None` + beszédes jelzés a State-ben, nem csendes 0.
- [ ] A JSON csak egyszer olvasódik (cache).

## Teszt-ötletek
- Fixture ranglistával 2 ismert csapatra assert.
- Ismeretlen tla → `None` + note.
