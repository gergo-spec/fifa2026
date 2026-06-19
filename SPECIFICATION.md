# Meccsjósló — Specifikáció

Verzió: v1 (2026-06-19). Hatókör: 2026-os FIFA World Cup egyetlen le nem
játszott meccsének kimenet-jóslása, LLM-mel, LangGraph gráfban.

---

## 1. Cél és nem-cél

**Cél:** egy közelgő WC-meccsre három kimenet-valószínűséget (hazai győzelem /
döntetlen / vendég győzelem) + várható gólszámot + rövid indoklást adni,
strukturált jelek alapján, **kalibrálható** módon. Napi futás a következő 48
óra meccseire, CSV-naplóval.

**Nem-cél (v1):**
- Nincs Brier-score / evaluate node — a CSV-t külön repó tool értékeli ki.
- Nincs odds-alapú jel (tilos).
- Nincs Elo.
- Nincs utazási távolság / úti-pihenő különbség (backlog).
- Nincs élő/menet közbeni (in-play) jóslás.

---

## 2. Bemenet

Egy meccset a napi entrypoint a football-data `/competitions/WC/matches`
végpontból szed ki (következő 48h, `utcDate` alapján pontosan szűrve). Egy
meccsből kiolvasott bemeneti mezők a State-be:

| Mező | Forrás | Példa |
|---|---|---|
| `match_id` | `matches[].id` | `537358` |
| `utc_date` | `utcDate` | `2026-06-20T18:00:00Z` |
| `home_tla` / `away_tla` | `homeTeam.tla` / `awayTeam.tla` | `ARG` / `FRA` |
| `home_name` / `away_name` | `homeTeam.name` / `awayTeam.name` | |
| `stage` | `stage` | `GROUP_STAGE` |
| `group` | `group` (csak csoportkör) | `GROUP_C` |
| `venue` | `/matches/{id}` `venue` | `Estadio Azteca` |
| `competition` | konstans | `WC` |

> Az `odds` mezőt **nem** olvassuk be.

---

## 3. State (közös állapot)

Egy `TypedDict` (LangGraph `StateGraph` állapot). A node-ok csak hozzáírnak.

```
# --- bemenet ---
match_id, utc_date, home_tla, away_tla, home_name, away_name,
stage, group, venue, competition

# --- nyersadat ---
home_rank, away_rank, home_points, away_points, rank_diff          # get_rankings
home_recent_matches, away_recent_matches, h2h                       # get_previous_matches
group_standings                                                     # get_group_standings (csak csoportkör)

# --- származtatott jellemzők (derive_features) ---
home_form, away_form          # forma: utolsó 5 meccs súlyozott pont/győzelmi arány
home_fatigue, away_fatigue    # {rest_days, matches_in_window}
home_goals, away_goals        # {attack: lőtt gólátlag, defense: kapott gólátlag}
host_advantage                # melyik csapat (ha van) házigazda-nemzet
venue_altitude_m, venue_climate   # a meccs helyszínéből

# --- kimenet (predict) ---
prob_home, prob_draw, prob_away   # összegük ≈ 1.0
expected_goals_home, expected_goals_away
rationale                          # 1-2 mondat
```

---

## 4. Node-ok

### 4.1 `get_rankings`
- Beolvassa a helyi `data/fifa_ranking_2026-06-11.json`-t (egyszer, cache).
- `home_tla` / `away_tla` alapján kikeresi a `rank` és `points` értékeket.
- Számolja: `rank_diff = away_rank - home_rank` (pozitív → hazai erősebb).
- Hiányzó tla esetén: explicit hiba/jel a State-ben (ne csendben 0).

### 4.2 `get_previous_matches`
- Forrás: **H2H + WC tornán belüli meccsek** (free tier-kompatibilis).
  - `GET /matches/{match_id}/head2head?limit=N` → `h2h` (aggregátum + meccsek).
  - Mindkét csapat tornán belül **FINISHED** meccsei a `/competitions/WC/matches`
    listából `tla` szerint szűrve → `home_recent_matches`, `away_recent_matches`.
- `N` konfigból (`RECENT_N`, default 5).
- A torna elején kevés/0 meccs lehet → ezt a derive_features és a predict
  kezeli (kis mintára óvatos jel).

### 4.3 `derive_features`
A nyers meccsekből három fő jel + venue-jelek. Determinisztikus Python.
- **forma** (`*_form`): utolsó max 5 meccs eredménye pontra váltva (győzelem 3,
  döntetlen 1, vereség 0), **frissebb meccs nagyobb súllyal** (pl. lineáris
  vagy exponenciális súly), normalizált [0,1] forma-szám + győzelmi arány.
- **fáradtság** (`*_fatigue`): `rest_days` = napok az utolsó meccs óta a
  `utc_date`-ig; `matches_in_window` = meccsek száma egy ablakban (pl. 14 nap).
  **Utazási távolság NINCS v1-ben.**
- **gólok** (`*_goals`): lőtt gólátlag (attack) és kapott gólátlag (defense) az
  elérhető meccsekből.
- **házigazda** (`host_advantage`): a `HOST_NATIONS = {USA, MEX, CAN}` halmaz
  alapján melyik csapat (ha van) játszik hazai pályán.
- **klíma/magasság** (`venue_altitude_m`, `venue_climate`): a meccs `venue`-je
  alapján a `data/venues.json`-ból.

### 4.4 `get_group_standings` (csak `stage == GROUP_STAGE`)
- `GET /competitions/WC/standings` → a meccs `group`-jának tabellája.
- **Csak a nyers állást adja át** (position, points, goalDifference, playedGames,
  won/draw/lost mezők mindkét csapatra + a csoport teljes sora).
- A motiváció-értelmezést **nem itt** számoljuk — az LLM dolga (lásd 4.5).

### 4.5 `predict` (LLM — Gemini)
- Megkapja az összes jelet **strukturáltan** (nem nyers JSON-dömping; tömör,
  címkézett összefoglaló).
- Csoportkörben a nyers állásból **az LLM vezeti le a motivációt** (forgatókönyv:
  már továbbjutott → lazíthat; kiesett → nincs tét; konkrét gólkülönbség kell →
  maximális tét).
- **Strukturált kimenetet** ad (JSON / structured output):
  `prob_home`, `prob_draw`, `prob_away` (összeg ≈ 1.0, normalizáljuk),
  `expected_goals_home`, `expected_goals_away`, `rationale` (1-2 mondat).
- **Tilos** odds-ra hivatkoznia. **Mindig 3 valószínűség**, sosem egy tipp.
- Hőmérséklet alacsony (determinizmus-barát), de a kalibráció a logokból jön.

---

## 5. Gráf (LangGraph)

- `START → get_rankings`, `START → get_previous_matches` (párhuzamos).
- `get_rankings → derive_features`, `get_previous_matches → derive_features`
  (fan-in; a derive_features mindkettő után fut).
- `derive_features →` **feltételes él**:
  - ha `stage == GROUP_STAGE` → `get_group_standings → predict`
  - különben → `predict`
- `predict → END`.
- A CSV-naplózást az entrypoint végzi a gráf után (vagy egy záró node) — a
  séma stabil (lásd 7.).

---

## 6. Napi entrypoint (`main.py`)

1. Betölti a configot (`.env`, FIFA JSON, venues JSON).
2. Lekéri a következő **48 óra** WC-meccseit (`dateFrom`=ma, `dateTo`=ma+2,
   majd `utcDate` szerint pontos 48h szűrés; `status` SCHEDULED/TIMED).
3. Minden meccsre lefuttatja a gráfot.
4. Minden eredményt **CSV-be append-el** (`predictions.csv`).
5. Rate limit tisztelet: a football-data hívások közt ~6 mp szünet, vagy a
   `X-Requests-Available-Minute` fejléc figyelése.
- Idempotencia: ugyanarra a `match_id`+futásnapra ne duplázzon (a CSV-ben
  jelölhető, vagy a kiértékelő tool dedup-ol — v1-ben elég append + `run_date`).

---

## 7. CSV-séma (`predictions.csv`)

Stabil oszlopsorrend (a külső kiértékelő tool erre épít). Fejléc egyszer.

```
run_date, match_id, utc_date, stage, group,
home_tla, away_tla, home_name, away_name,
home_rank, away_rank, rank_diff,
prob_home, prob_draw, prob_away,
expected_goals_home, expected_goals_away,
rationale
```

- `run_date`: a futtatás ISO dátuma (UTC).
- Tizedes pont (nem vessző), UTF-8, idézőjelezett `rationale`.

---

## 8. Konfiguráció / konstansok

| Név | Default | Jelentés |
|---|---|---|
| `FOOTBALL_DATA_BASE` | `https://api.football-data.org/v4` | URL séma+verzió hozzáfűzve |
| `COMPETITION` | `WC` | verseny kód |
| `RECENT_N` | `5` | utolsó N meccs a formához |
| `FORM_WINDOW_DAYS` | `14` | fáradtság-ablak |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | predict modell — a `.env` `GEMINI-MODEL` kulcsából felülírható |
| `HOST_NATIONS` | `{USA, MEX, CAN}` | házigazda-nemzetek |
| `RANKING_FILE` | `data/fifa_ranking_2026-06-11.json` | |
| `VENUES_FILE` | `data/venues.json` | |
| `OUTPUT_CSV` | `predictions.csv` | |
| `RATE_LIMIT_SLEEP_S` | `6` | hívások közti szünet |

---

## 9. `data/venues.json` séma

A 16 VB-helyszínre (USA/MEX/CAN). A `venue` névvel kulcsolva (football-data
`venue` mező), vagy város szerint, alias-listával a robusztus párosításhoz.

```json
{
  "Estadio Azteca": { "city": "Mexico City", "country": "MEX", "altitude_m": 2240, "climate": "high-altitude" },
  "MetLife Stadium": { "city": "East Rutherford", "country": "USA", "altitude_m": 5, "climate": "temperate" }
}
```

Mezők: `city`, `country` (tla), `altitude_m`, `climate` (pl. `temperate`,
`hot-humid`, `hot-dry`, `high-altitude`). A párosítás legyen tűrő (ismeretlen
venue → semleges jel, ne hiba).

---

## 10. Hibakezelés / élek

- Hiányzó FIFA-rank (tla nincs a listában) → jelölés a State-ben, az LLM
  kapja meg, hogy „ismeretlen rang".
- 0 korábbi meccs (torna eleje) → forma/gól jelek „insufficient data", a
  predict erre óvatosabb (a ranglista dominál).
- football-data 429 (rate limit) → backoff + retry.
- Ismeretlen venue → semleges klíma/magasság jel.
- Az LLM válasza nem normalizált / hibás JSON → 1× újrapróba szigorúbb
  prompttal; tartós hiba → a sor kihagyása + log.

---

## 11. Tesztelési elv

- TDD, story-nként (`spec/stories/`).
- A football-data és a Gemini hívások **mockolva** (rögzített fixture-ök
  `tests/fixtures/`-ben).
- A `derive_features` és a CSV-séma tiszta, determinisztikus → magas
  unit-lefedettség.
- A gráf feltételes ága mindkét ágra (csoport / kieséses) tesztelt.
