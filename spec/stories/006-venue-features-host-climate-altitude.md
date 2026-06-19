# Story 006 — Venue-jelek: házigazda, klíma, magasság

## Cél
A meccs helyszínéből származó jelek a State-be.

## Indoklás
VB 2026-ra releváns: házigazda-előny (USA/MEX/CAN) és klíma/magasság
(pl. Mexikóváros). Utazási távolság NEM v1.

## Hatókör
- `data/venues.json` (16 helyszín: `city`, `country`, `altitude_m`, `climate`),
  tűrő párosítás (alias/város), ismeretlen → semleges jel.
- A `derive_features` (vagy külön helper) State-be írja:
  - `host_advantage`: `home`/`away`/`none` — a `HOST_NATIONS = {USA,MEX,CAN}`
    alapján melyik csapat házigazda-nemzet.
  - `venue_altitude_m`, `venue_climate` a meccs `venue`-jéből.
- A venues.json-t fel kell tölteni a 16 valós helyszínnel (külön adatfeladat).

## Elfogadási kritériumok
- [ ] MEX hazai csapatként → `host_advantage="home"`.
- [ ] Egyik sem házigazda → `host_advantage="none"`.
- [ ] Estadio Azteca → `altitude_m≈2240`, `climate="high-altitude"`.
- [ ] Ismeretlen venue → semleges (`altitude_m=None`/0, `climate="unknown"`), nincs hiba.

## Teszt-ötletek
- Venue fixture → magasság/klíma assert.
- Host-nemzet mátrix (home host / away host / none).
