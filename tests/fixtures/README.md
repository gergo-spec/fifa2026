# Tesztadat — football-data.org fixture-ök

A `tests/fakes.py`-beli `FakeFootballDataSite` szolgálja ki ezeket, valós HTTP
helyett. A négy megjósolandó meccs a megadott menetrend (június 21., vasárnap):

| Kezdés (CEST) | Kezdés (UTC, fixture) | Csoport | Meccs | match_id | venue |
|---|---|---|---|---|---|
| 02:00 | `2026-06-21T00:00:00Z` | E | Ecuador (ECU) – Curaçao (CUW) | 537401 | Estadio Azteca (MEX, 2240 m) |
| 06:00 | `2026-06-21T04:00:00Z` | F | Tunézia (TUN) – Japán (JPN)   | 537402 | Hard Rock Stadium (USA) |
| 18:00 | `2026-06-21T16:00:00Z` | H | Spanyolország (ESP) – Szaúd-Arábia (KSA) | 537403 | MetLife Stadium (USA) |
| 21:00 | `2026-06-21T21:00... → 19:00:00Z` | G | Belgium (BEL) – Irán (IRN) | 537404 | BMO Field (CAN) |

> A képen magyar idő (CEST = UTC+2) látszik; a fixture-ök UTC-ben tárolják
> (`utcDate`), ahogy a valós API. A 21:00 CEST → 19:00 UTC.

## Fájlok

| Fájl | Mit ad vissza | Végpont |
|---|---|---|
| `matches_upcoming.json` | a 4 SCHEDULED meccs | `/competitions/WC/matches?dateFrom&dateTo` |
| `matches_finished.json` | 16 lejátszott csoportmeccs (forduló 1–2) | `/competitions/WC/matches?status=FINISHED` |
| `match_details.json` | meccsenként a részlet + `venue` (id szerint) | `/matches/{id}` |
| `head2head.json` | meccsenként a H2H (id szerint) | `/matches/{id}/head2head` |
| `standings.json` | E/F/G/H csoportok tabellája (2 forduló után) | `/competitions/WC/standings` |
| `rate_limit_429.json` | a 429-es válasz body-ja | (rate limit) |

A `tests/fixtures/venues.json` a venue→ország/magasság/klíma teszttábla
(Story 006); a valós `data/venues.json` külön adatfeladat.

## Feltételezések / szándékos tulajdonságok

- **A csoportösszeállítás szintetikus.** Mivel a 2026-os sorsolás nem ismert, a
  négy csoportot a `fifa_ranking_2026-06-11.json` csapataiból állítottam össze
  (E: ECU/CUW/NOR/EGY, F: TUN/JPN/CRO/PAN, G: BEL/IRN/SEN/HAI, H:
  ESP/KSA/URU/SCO). A `tla`-k és FIFA-helyezések valósak.
- **Az állás motiváció-forgatókönyveket feszít** (az LLM ebből vezeti le a
  motivációt, lásd Story 009):
  - E: ECU már gyakorlatilag továbbjutott (6 pont), CUW kiesés szélén (1 pont).
  - F: TUN-nak **győznie kell** a JPN ellen a továbbjutáshoz (3 vs 4 pont).
  - G: BEL és IRN is 4 ponton — a győztes nagy eséllyel csoportelső.
  - H: ESP közel a továbbjutáshoz, KSA-nak (1 pont) nagy győzelem kell.
- Az `odds` mező **szándékosan benne van** a fixture-ökben (a valós csomag
  „aktiváld" üzenetével); a valós kliens feladata kiszűrni — ezt teszt fedi.
- A meccs-id-k (537401–537404, 5373xx) és csapat-id-k kitaláltak, de
  konzisztensek; a `tla` és az eredmények egymással is konzisztensek
  (`winner` ↔ `fullTime`), amit teszt ellenőriz.

## Rate limit (10 kérés/perc)

A `FakeFootballDataSite` `limit=10`, `window_s=60` csúszóablakot szimulál: a
keret elfogyásakor **429** + `Retry-After` + `X-Requests-Available-Minute: 0`.
`ManualClock`-kal determinisztikusan tesztelhető a kliens várakozó/retry
viselkedése — lásd `tests/test_fixtures_and_fake_site.py`.

Futtatás:

```bash
uv run python tests/fakes.py     # gyors önteszt a fixture-ökre
uv run pytest -q                 # a teljes validáló tesztkészlet
```
