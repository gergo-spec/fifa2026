# Story 007 — `get_group_standings` node (csak csoportkör)

## Cél
A meccs csoportjának nyers tabellája a State-be, csoportkörben.

## Indoklás
A motivációhoz a forgatókönyv kell, nem a tabella maga — de a nyers állást a
node adja, az **értelmezést az LLM** végzi (lásd Story 009).

## Hatókör
- `nodes/get_group_standings.py`, `FootballDataClient.standings()`.
- A meccs `group`-jának tabellája → `group_standings`:
  csoport teljes sora + mindkét csapat `position`, `points`, `goalDifference`,
  `playedGames`, `won/draw/lost`.
- **Nincs** motiváció-számítás itt (nyers átadás).
- Csak `stage == GROUP_STAGE` esetén fut (a gráf feltételes éle vezérli).

## Elfogadási kritériumok
- [ ] A helyes csoport tabellája kerül a State-be.
- [ ] Mindkét csapat sora azonosítva (tla/név alapján).
- [ ] Nincs származtatott „motiváció" mező — csak nyers állás.
- [ ] API mockolt.

## Teszt-ötletek
- Standings fixture → adott group kiválasztása.
- Két csapat sorának kiemelése.
