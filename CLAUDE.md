# CLAUDE.md — Meccsjósló

LangGraph alapú alkalmazás, ami egy **le nem játszott** labdarúgó-meccs
kimenetét jósolja meg. A jóslást maga az **LLM** végzi (Gemini); a node-ok
csak adatot gyűjtenek és strukturált jeleket számolnak hozzá.

Cél: 2026-os FIFA World Cup (football-data.org `WC` competition).

## Stack

- **Python** + **LangGraph** (nem sima LangChain — feltételes elágazás kell:
  csoportkör ↔ egyenes kieséses szakasz).
- **Predict LLM:** Google **Gemini 3.1 Flash Lite** (`langchain-google-genai`).
  A modell-id a **`.env`-ből** jön (`GEMINI-MODEL` kulcs), default
  `gemini-3.1-flash-lite` — így kód-módosítás nélkül cserélhető.
- Adatforrás: **football-data.org v4** API + helyi **FIFA-ranglista JSON**.
- Futás: napi **cron / agent-core** trigger, ami a következő **48 óra**
  WC-meccseit jósolja meg, és **CSV**-be naplóz.

## Fejlesztői parancsok (uv)

A projekt **`uv`**-vel kezelt (NEM `pip`/`venv` kézzel). A függőségek a
`pyproject.toml`-ban, a lockfile a `uv.lock`.

```bash
uv sync                       # függőségek telepítése a .venv-be (lockfile alapján)
uv run meccsjoslo             # napi futás (entrypoint)
uv run python -m meccsjoslo.main
uv run pytest                 # tesztek
uv run pytest tests/test_x.py -q
uv add <csomag>               # új runtime függőség
uv add --dev <csomag>         # új fejlesztői függőség
```

- Mindig `uv run ...`-nal futtass (a megfelelő `.venv`-et használja); ne hívj
  csupasz `python`/`pytest`-et.
- Új függőség: `uv add`, ne kézzel szerkeszd a `pyproject.toml` deps listáját.

## Fő megkötések (kemény szabályok)

- **Odds tilos.** A jóslás nem használhat fogadóirodai szorzót. A
  football-data `odds` mezőjét tilos beolvasni/átadni az LLM-nek.
- **Nincs Elo.** Csapaterő kizárólag a **FIFA-világranglista** (helyezés +
  pont + helyezéskülönbség).
- **A predict node MINDIG 3 valószínűséget ad** (hazai / döntetlen / vendég),
  sosem egyetlen tippet — különben nem kalibrálható. Plusz várható gólszám +
  1-2 mondat indoklás.
- A valószínűségek **összege ≈ 1.0** (normalizálva).

## Folyamat (gráf)

```
match input (48h ablakból)
   ├─> get_rankings ──────────┐
   └─> get_previous_matches ──┘
              v
        derive_features  (forma, fáradtság, gólok, házigazda, klíma/magasság)
              v
        csoportkör? ── igen ─> get_group_standings (nyers állás) ─┐
              └──────── nem ───────────────────────────────────────┤
                                                                    v
                                                              predict (Gemini)
                                                                    v
                                                            CSV log
```

- `get_rankings` + `get_previous_matches` **párhuzamos** ágak, fan-in a
  `derive_features`-nél.
- A **motiváció** nem determinisztikus: `get_group_standings` csak a **nyers
  csoportállást** adja át, a forgatókönyv-értelmezést (továbbjutott / kiesett /
  konkrét gólkülönbség kell) az **LLM** végzi a predict node-ban.
- **Evaluate / Brier-score nincs ebben a repóban.** A CSV-naplót egy külön
  repóban készülő tool értékeli ki később — a CSV-séma stabil maradjon.

## tipp.ly publikálás (opcionális)

A jóslat **pontos eredmény** tippjét (kerekített expected goals) fel lehet tenni a
**tipp.ly** oldalra böngésző-automatizálással (Playwright + Gemini locate). Az
`src/meccsjoslo/tipply/` csomag (a korábbi külön projekt beépített portja).

- **Kapuzott, opcionális:** csak `TIPPLY_PUBLISH=1` + `TIPPLY_EMAIL`/`TIPPLY_PASSWORD`
  esetén fut; egyébként `make_tipply_sink(...)` `None` → no-op. A
  `run_once(on_result=...)` horogba kötve, meccsenként.
- **Dry-run alapból**, tényleges mentés csak `TIPPLY_SUBMIT=1`.
- **Csapatnevek:** a fixture-guard a magyar neveket várja → `data/teams_hu.json`
  (TLA→magyar). Angol nevek a nem-rokon eseteknél elbuknának.
- **Locate LLM:** `langchain-google-genai` (`with_structured_output(LocatePlan)`),
  a meglévő `GEMINI-API-KEY`/`GEMINI-MODEL`-lel.
- **Session:** `storage_state.json` (bejelentkezett tipp.ly session) a projektgyökérben
  (`TIPPLY_STORAGE_STATE`-tel felülírható). **Gitignore** – titok, nem commitba.
- **Guardrailek:** bot-wall stop, confidence gate, fixture-guard, idempotencia
  (létező tipp skip), read-back verify; egy meccs/böngésző-session, ember-tempó.
- A böngészőhöz: `uv run playwright install chromium` (+ WSL: `sudo uv run
  playwright install-deps chromium`).

## Projektstruktúra (cél)

```
pyproject.toml           # uv projekt + függőségek
uv.lock                  # uv lockfile
src/meccsjoslo/
  config.py              # .env betöltő (kettőspontos formátum!), konstansok
  state.py               # közös State (TypedDict)
  graph.py               # LangGraph összeállítás + feltételes él
  main.py                # napi entrypoint: 48h meccsek → graph → CSV
  clients/
    football_data.py     # v4 API kliens (X-Auth-Token, rate-limit tudat)
  nodes/
    get_rankings.py
    get_previous_matches.py
    derive_features.py
    get_group_standings.py
    predict.py
  logging_csv.py         # jóslat → CSV append
  tipply/                # opcionális tipp.ly publikálás (Playwright + Gemini locate)
    sink.py              # on_result sink: result → Match/Score, kapuzott
    publisher.py, browser.py, login.py, fill.py, verify.py, submit.py
    locate.py, llm.py, fixtures.py, snapshot.py, state.py, config.py
data/
  fifa_ranking_2026-06-11.json   # FIFA ranglista (48 csapat, tla kulcs)
  venues.json                    # 16 helyszín: ország, magasság, klíma
  teams_hu.json                  # TLA → magyar csapatnév (tipp.ly fixture-illesztés)
storage_state.json       # tipp.ly bejelentkezett session (gitignore)
tests/
spec/
  stories/               # TDD story-k
SPECIFICATION.md
predictions.csv          # kimenet (gitignore)
```

## `.env` formátum (FONTOS)

A `.env` soronként `KULCS<elválasztó>ÉRTÉK`. A betöltő **mind a `:`, mind a `=`**
elválasztót elfogadja (a sorban előbb előfordulót), így a vegyes `.env` is
működik (football-data `:`, Langfuse/Gemini gyakran `=`):

```
FOOTBALL-DATA-API-KEY:<kulcs>
FOOTBALL-DATA-URL:football-data.org
GEMINI-API-KEY=<kulcs>
GEMINI-MODEL=gemini-3.1-flash-lite
LANGFUSE_PUBLIC_KEY=<kulcs>
LANGFUSE_SECRET_KEY=<kulcs>
LANGFUSE_BASE_URL=<host, pl. http://localhost:3000>
# opcionális tipp.ly publikálás:
TIPPLY_EMAIL=<email>
TIPPLY_PASSWORD=<jelszó>
TIPPLY_PUBLISH=1          # inline publikálás be (0/üres = ki)
TIPPLY_SUBMIT=0          # 1 = tényleges mentés, különben dry-run
```

## Observability (Langfuse)

Az LLM-hívások **Langfuse**-ba naplózódnak, ha a fenti három `LANGFUSE_*` kulcs
megvan (különben a predikció Langfuse nélkül fut). Bekötés: `config.langfuse_client()`
+ `gemini_predictor(..., langfuse=client)` — minden Gemini-hívás egy „generation"
span (modell, prompt, válasz). A `scripts/live_predict.py` meccsenként egy „chain"
szülő-span alá rendezi a futást. A rövid életű folyamat végén `langfuse.flush()` kell.

- A `FOOTBALL-DATA-URL` séma (`https://`) és verzió (`/v4`) nélküli — a kódban
  kell hozzáfűzni: `https://api.football-data.org/v4`.
- A `.env` titkos, soha ne kerüljön be kódba/commitba. A `.env.example` a minta.

## football-data.org tudnivalók

- Auth: `X-Auth-Token: <kulcs>` fejléc.
- Rate limit (free): **10 kérés/perc** — batch lekérésnél ~6 mp szünet, vagy a
  `X-Requests-Available-Minute` fejléc figyelése.
- Minden időpont **UTC** (`utcDate`).
- `stage`: `GROUP_STAGE`, `LAST_16`, `QUARTER_FINALS`, `SEMI_FINALS`, `FINAL`.
- `group` csak csoportkörben van (pl. `GROUP_F`).
- Releváns végpontok: `/competitions/WC/matches`, `/matches/{id}/head2head`,
  `/competitions/WC/standings`, `/competitions/WC/teams`.
- A football-data **NEM ad FIFA-ranglistát** → helyi JSON-ból, `tla` kulcs
  szerint párosítva.

## Fejlesztési mód

- **TDD.** Minden funkció egy `spec/stories/`-beli story-hoz horgonyzott, és a
  red → green → refactor ciklust követi (lásd `/tdd` skill).
- Az API-t hívó node-okat tesztben **mockoljuk** (rate limit + determinizmus).
- Kód-identifikátorok angolul; kommentek/dokumentáció magyarul.
- Részletek: `SPECIFICATION.md`.
