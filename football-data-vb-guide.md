# football-data.org – VB 2026 lekérdezési guide

Gyakorlati útmutató a 2026-os FIFA World Cup adatainak lekéréséhez a
[football-data.org](https://www.football-data.org) v4 API-val.
Minden példa tesztelve a saját kulcsoddal (2026-06-15).

---

## 0. Alapok

| Tulajdonság | Érték |
|---|---|
| Base URL | `https://api.football-data.org/v4` |
| Auth fejléc | `X-Auth-Token: <API_KEY>` |
| VB verseny kód | `WC` (vagy ID: `2000`) |
| Aktuális szezon | 2026-06-11 → 2026-07-19 |
| Csapatok száma | 48 |
| Free tier rate limit | **10 kérés / perc** |

### Kulcs betöltése a `.env`-ből

A `.env` formátuma **kettősponttal** elválasztott (nem `KULCS=ÉRTÉK`!):

```
FOOTBALL-DATA-API-KEY:<a kulcs>
FOOTBALL-DATA-URL:football-data.org
```

> ⚠️ A `FOOTBALL-DATA-URL` érték nem tartalmaz sémát (`https://`) és verziót
> (`/v4`). A kódban fűzd hozzá, vagy javítsd a `.env`-ben teljes URL-re.

Python betöltő (ezt használja az összes lenti példa):

```python
import urllib.request, urllib.error, json

def load_token(path="/home/gergo/job/apisport/.env"):
    cfg = {}
    for line in open(path):
        if ":" in line:
            k, v = line.split(":", 1)
            cfg[k.strip()] = v.strip()
    return cfg["FOOTBALL-DATA-API-KEY"]

BASE = "https://api.football-data.org/v4"
TOKEN = load_token()

def api_get(path):
    req = urllib.request.Request(BASE + path, headers={"X-Auth-Token": TOKEN})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)
```

curl megfelelője:

```bash
curl -s -H "X-Auth-Token: <API_KEY>" \
  "https://api.football-data.org/v4/competitions/WC/matches"
```

---

## 1. A következő 48 óra VB-meccsei

A `matches` végpont `dateFrom` és `dateTo` szűrőt fogad (ISO `YYYY-MM-DD`,
UTC nap szerint, max ~10 nap tartomány).

```python
import datetime

def next_48h_matches():
    now = datetime.datetime.utcnow()
    d_from = now.date().isoformat()
    d_to   = (now.date() + datetime.timedelta(days=2)).isoformat()
    data = api_get(f"/competitions/WC/matches?dateFrom={d_from}&dateTo={d_to}")

    cutoff = now + datetime.timedelta(hours=48)
    for m in data["matches"]:
        kickoff = datetime.datetime.fromisoformat(m["utcDate"].replace("Z", ""))
        if now <= kickoff <= cutoff:                      # pontos 48h ablak
            print(f"{m['utcDate']} | {m['stage']} {m.get('group','')} | "
                  f"{m['homeTeam']['name']} vs {m['awayTeam']['name']} "
                  f"[{m['status']}]")

next_48h_matches()
```

curl-lel (a dátumokat helyettesítsd):

```bash
curl -s -H "X-Auth-Token: <API_KEY>" \
  "https://api.football-data.org/v4/competitions/WC/matches?dateFrom=2026-06-15&dateTo=2026-06-17"
```

> 💡 A `dateTo` napszintű, ezért 2 napos tartományt kérünk le, majd kódban
> szűrünk a pontos 48 órás ablakra a `utcDate` alapján.

### Egy meccs objektum mezői

```
area, competition, season, id, utcDate, status, venue, matchday,
stage, group, lastUpdated, homeTeam, awayTeam, score, odds, referees
```

- **status**: `SCHEDULED` / `TIMED` / `IN_PLAY` / `PAUSED` / `FINISHED` / `POSTPONED`
- **stage**: pl. `GROUP_STAGE`, `LAST_16`, `QUARTER_FINALS`, `SEMI_FINALS`, `FINAL`
- **group**: pl. `GROUP_F` (csak csoportkörben)
- **score**: `winner`, `duration`, `fullTime{home,away}`, `halfTime{home,away}`
- **homeTeam/awayTeam**: `id`, `name`, `tla` (3 betűs kód), `crest` (címer URL)
- **referees**: játékvezetők neve, típusa, nemzetisége
- **venue**: a meccs helyszíne (egyedi meccs-lekérésnél töltve)

### További szűrők a `matches` végponton

| Paraméter | Példa | Jelentés |
|---|---|---|
| `status` | `status=SCHEDULED` | csak adott állapotú meccsek |
| `matchday` | `matchday=1` | adott forduló |
| `stage` | `stage=GROUP_STAGE` | adott szakasz |
| `dateFrom`/`dateTo` | lásd fent | időtartomány |

Globális verzió (összes verseny egyszerre, nem csak VB):
`/matches?competitions=2000&dateFrom=...&dateTo=...`

---

## 2. Oddsok (fogadási szorzók)

Az `odds` mező **minden meccsen jelen van**, de a free csomagban így néz ki:

```json
"odds": { "msg": "Activate Odds-Package in User-Panel to retrieve odds." }
```

➡️ **Az oddsokat külön kell aktiválni** a football-data.org user paneljében
(fizetős / külön igényelhető „Odds-Package"). Aktiválás után ugyanennek a
mezőnek a tartalma a szorzókkal (1X2: hazai/döntetlen/vendég) töltődik fel,
nincs külön végpont – ugyanazon a `/matches` és `/matches/{id}` válaszon
belül érkezik.

Teendő:
1. Lépj be: <https://www.football-data.org/client/home>
2. User Panel → aktiváld az Odds-Package-et.
3. Utána az `odds` mező a meccsenkénti szorzókat adja vissza (a kód nem
   változik, ugyanazt a végpontot hívod).

> A free tier-en oddsra ne építs – tervezz az aktivált csomaggal, vagy
> külön odds-szolgáltatóval (pl. The Odds API), és csak a meccs-azonosítást
> (csapatok, kezdés) vedd a football-data-ból.

---

## 3. Milyen egyéb adatokat lehet kideríteni?

Mind tesztelve VB-re. Figyelj a 10 kérés/perc limitre (a válasz
`X-Requests-Available-Minute` fejlécében látod a maradékot).

### 3.1 Csoportállás / tabella – `/competitions/WC/standings`

Csoportonként (`Group A` … ) külön tabella. Egy sor mezői:

```
position, team, playedGames, form, won, draw, lost,
points, goalsFor, goalsAgainst, goalDifference
```

```python
data = api_get("/competitions/WC/standings")
for grp in data["standings"]:
    print(grp["group"])
    for row in grp["table"]:
        print(f"  {row['position']}. {row['team']['name']:15} "
              f"{row['points']}p {row['goalsFor']}-{row['goalsAgainst']}")
```

### 3.2 Góllövőlista – `/competitions/WC/scorers?limit=N`

Mezők: `player`, `team`, `goals`, `assists`, `penalties`, `playedMatches`.

```python
data = api_get("/competitions/WC/scorers?limit=10")
for s in data["scorers"]:
    print(f"{s['goals']} gól – {s['player']['name']} ({s['team']['name']})")
```

### 3.3 Csapatok + keret – `/competitions/WC/teams`

48 csapat. Egy csapat mezői:

```
area, id, name, shortName, tla, crest, address, website, founded,
clubColors, venue, runningCompetitions, coach, squad, staff, lastUpdated
```

- **coach**: szövetségi kapitány (név, nemzetiség, szerződés)
- **squad**: teljes keret (játékos név, pozíció, mez, születési dátum, nemzetiség)
- **staff**: stáb

```python
data = api_get("/competitions/WC/teams")
for t in data["teams"]:
    coach = (t.get("coach") or {}).get("name")
    print(f"{t['name']} – kapitány: {coach}, keret: {len(t.get('squad',[]))} fő")
```

### 3.4 Egy meccs részletei – `/matches/{id}`

Ugyanaz a struktúra, mint a listában, de tartalmazza a `venue` mezőt és a
végeredmény + félidei eredmény + játékvezetők részleteit.

### 3.5 Egymás elleni mérleg (H2H) – `/matches/{id}/head2head?limit=N`

A két csapat korábbi találkozói és összegzés:

```python
data = api_get("/matches/537358/head2head?limit=10")
agg = data["aggregates"]
print(f"Összes meccs: {agg['numberOfMatches']}, összgól: {agg['totalGoals']}")
print(f"{agg['homeTeam']['name']}: {agg['homeTeam']['wins']} győzelem")
print(f"{agg['awayTeam']['name']}: {agg['awayTeam']['wins']} győzelem")
for m in data["matches"]:
    print(m["utcDate"], m["homeTeam"]["name"], m["score"]["fullTime"], m["awayTeam"]["name"])
```

### 3.6 Verseny meta + korábbi kiírások – `/competitions/WC`

`currentSeason`, `emblem` (logó), és a `seasons` tömb a korábbi
világbajnokságokkal (23 szezon elérhető) – régi VB-k győztesei,
mérkőzései is lekérhetők a `season` ID-vel (`?season=<id>`).

### 3.7 Világranglista (FIFA ranking) – ⚠️ NINCS az API-ban

A football-data.org **nem ad FIFA-világranglista helyezést.** Tesztelve:
a csapat-objektumban (`/teams/{id}`) nincs semmilyen ranking mező, és külön
végpont sincs rá.

Amit „rangsor" jelleggel ad, az kizárólag a **tornán belüli csoportállás**
(`/competitions/WC/standings`, lásd 3.1) – ez nem a globális FIFA-ranglista.

**Honnan szerezhető be a FIFA-világranglista:**

| Forrás | Megjegyzés |
|---|---|
| [Hivatalos FIFA ranking](https://inside.fifa.com/fifa-world-ranking/men) | kézi / scrape |
| API-Football (api-sports.io) | csapat-statisztika, rankinget tartalmaz |
| SportMonks és egyéb sport-data API-k | fizetős, ranglistával |

Tipikus megoldás: a meccseket/eredményeket a football-data.org-ból veszed, a
FIFA-ranglistát egy másik forrásból egészíted hozzá, a csapat `tla` (3 betűs
kód) vagy név alapján párosítva.

#### Kész statikus lista: `fifa_ranking_2026-06-11.json`

Ehhez a projekthez letöltöttem a **2026-06-11-i hivatalos FIFA-világranglistát**
mind a 48 VB-csapatra, a football-data `tla` kód szerint kulcsolva. Szerkezet:

```json
{
  "rankingDate": "2026-06-11",
  "nextUpdate": "2026-07-20",
  "rankings": {
    "ARG": { "name": "Argentina", "rank": 1, "points": 1877.27 },
    "ESP": { "name": "Spain",     "rank": 2, "points": 1874.71 }
  }
}
```

> ℹ️ Statikus pillanatkép – a FIFA legközelebb **2026-07-20**-án frissít.
> Akkor cseréld a fájlt. Forrás: hivatalos FIFA top 20 + whereig.com/ESPN top 100.

Párosítás a football-data csapatokkal (`tla` alapján):

```python
import json
ranking = json.load(open("fifa_ranking_2026-06-11.json"))["rankings"]

teams = api_get("/competitions/WC/teams")["teams"]
for t in sorted(teams, key=lambda x: ranking.get(x["tla"], {}).get("rank", 999)):
    r = ranking.get(t["tla"])
    if r:
        print(f"#{r['rank']:>2} {t['name']:18} {r['points']} pont")
```

Meccs előnézethez a két csapat ranglista-helyét egymás mellé téve:

```python
m = api_get("/matches/537358")
h, a = m["homeTeam"]["tla"], m["awayTeam"]["tla"]
print(f"{m['homeTeam']['name']} (#{ranking[h]['rank']}) vs "
      f"{m['awayTeam']['name']} (#{ranking[a]['rank']})")
```

---

## 4. Összefoglaló végpont-térkép

| Cél | Végpont |
|---|---|
| Verseny meta + szezonok | `GET /competitions/WC` |
| Meccsek (szűrhető) | `GET /competitions/WC/matches?dateFrom&dateTo&status&matchday&stage` |
| Egy meccs | `GET /matches/{id}` |
| H2H | `GET /matches/{id}/head2head?limit=N` |
| Csoportállás | `GET /competitions/WC/standings` |
| Góllövők | `GET /competitions/WC/scorers?limit=N` |
| Csapatok + keret | `GET /competitions/WC/teams` |
| Egy csapat | `GET /teams/{id}` |
| **Oddsok** | `odds` mező a `/matches` válaszban – **Odds-Package aktiválás kell** |
| **FIFA-világranglista** | ❌ nincs – külső forrásból (lásd 3.7) |

## 5. Jó tudni / korlátok

- **Rate limit**: 10 kérés/perc (free). A `X-Requests-Available-Minute`
  fejlécből olvasd a maradékot; batch lekéréseknél tegyél ~6 mp szünetet.
- **Dátumszűrő**: napszintű és UTC. A pontos 48h ablakra a `utcDate`
  alapján kódban szűrj.
- **Időzóna**: minden időpont UTC (`utcDate`). Magyar időhöz +2h (nyári idő).
- **Címerek/logók**: `crest` és `emblem` mezőkben CDN URL-ek.
- **Oddsok**: free tier-en nem elérhetők, külön csomag szükséges.
