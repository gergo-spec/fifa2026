# Story 004 — `get_previous_matches` node

## Cél
Mindkét csapat korábbi meccsei + a H2H aggregátum a State-be (nyersadat).

## Indoklás
A forma, gólok és fáradtság-jelek alapja. Free tier-kompatibilis forrás: H2H +
tornán belüli FINISHED meccsek.

## Hatókör
- `nodes/get_previous_matches.py`, használja a `FootballDataClient`-et.
- `head2head(match_id, limit=RECENT_N)` → `h2h` (aggregátum + meccslista).
- `/competitions/WC/matches?status=FINISHED` → szűrés `home_tla` / `away_tla`-ra
  → `home_recent_matches`, `away_recent_matches` (max `RECENT_N`, `utcDate` szerint csökkenő).
- Minden meccsből csak a szükséges mezők: `utcDate`, gólok (`score.fullTime`),
  ellenfél, hazai/vendég oldal, competition.
- Torna eleje → üres listák megengedettek.

## Elfogadási kritériumok
- [ ] A két csapat FINISHED meccsei helyesen szűrve és rendezve.
- [ ] `h2h` aggregátum a State-ben (numberOfMatches, mindkét csapat győzelmei).
- [ ] 0 korábbi meccs esetén üres lista, nincs hiba.
- [ ] Nincs `odds` a tárolt mezők közt.
- [ ] API mockolt.

## Teszt-ötletek
- Fixture meccslista → szűrés egy tla-ra → várt meccsek.
- Üres torna-eset → üres listák.
