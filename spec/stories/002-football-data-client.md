# Story 002 — football-data.org v4 kliens

## Cél
Vékony kliens a football-data v4 API-hoz, auth-fejléccel és rate-limit
tudattal.

## Indoklás
Több node hív API-t; a hitelesítés, base URL, hibakezelés és a 10 kérés/perces
limit egy helyen legyen.

## Hatókör
- `clients/football_data.py`: `FootballDataClient(token, base)`.
- `get(path) -> dict`: `X-Auth-Token` fejléc, JSON parse.
- Kényelmi metódusok: `matches(date_from, date_to, status=None, stage=None)`,
  `match(match_id)`, `head2head(match_id, limit)`, `standings()`.
- Rate limit: 429 esetén backoff+retry; opcionálisan a
  `X-Requests-Available-Minute` fejléc kiolvasása.
- **Tilos** az `odds` mezőt visszaadni/továbbadni — szűrjük ki a válaszból.

## Elfogadási kritériumok
- [ ] A kérés `X-Auth-Token` fejlécet küld a configból.
- [ ] `matches()` helyesen építi a query stringet (`dateFrom`, `dateTo`, `status`, `stage`).
- [ ] 429 → backoff után újrapróba (mockolt).
- [ ] Az `odds` kulcs nincs a kliens által visszaadott meccs-objektumban.
- [ ] Hálózati hívás tesztben **mockolt** (nincs valós HTTP).

## Teszt-ötletek
- Mock HTTP → fejléc ellenőrzés.
- `matches(...)` URL-összeállítás assert.
- Válaszból az `odds` eltávolítva.

## Tesztadat / mock
- A `tests/fakes.py::FakeFootballDataSite` szolgálja ki a
  `tests/fixtures/football_data/` fixture-öket valós HTTP helyett, és
  **szimulálja a 10/perc rate limitet** (429 + `Retry-After` +
  `X-Requests-Available-Minute`), `ManualClock`-kal determinisztikusan.
- A kliens 429-re **`Retry-After` szerint várjon, majd próbálja újra**; a
  `sleep` és a `clock` injektálható legyen, hogy a várakozás tesztelhető legyen
  valós idő nélkül.
- A négy megjósolandó meccs (ECU–CUW, TUN–JPN, ESP–KSA, BEL–IRN) adatai már
  készen állnak — lásd `tests/fixtures/README.md`.
