# Meccsjósló

LangGraph alapú alkalmazás, ami egy le nem játszott labdarúgó-meccs kimenetét
jósolja meg LLM-mel (Gemini), CSV-be és Langfuse-ba naplóz, és **opcionálisan** a
tippet (pontos eredmény) felteszi a **tipp.ly** oldalra. Részletek:
[`CLAUDE.md`](CLAUDE.md) és [`SPECIFICATION.md`](SPECIFICATION.md).

## Telepítés

```bash
uv sync                                  # függőségek a .venv-be
uv run playwright install chromium       # csak a tipp.ly publikáláshoz kell
# WSL-en a böngésző OS-libjei (root kell):
# sudo uv run playwright install-deps chromium
```

A titkok a `.env`-ben (a betöltő `:` és `=` elválasztót is elfogad). Minimum:

```
FOOTBALL-DATA-API-KEY:<kulcs>
GEMINI-API-KEY=<kulcs>
GEMINI-MODEL=gemini-3.1-flash-lite       # opcionális, ez a default
# opcionális Langfuse:
LANGFUSE_PUBLIC_KEY=<kulcs>
LANGFUSE_SECRET_KEY=<kulcs>
LANGFUSE_BASE_URL=http://localhost:3000
# opcionális tipp.ly publikálás:
TIPPLY_EMAIL=<email>
TIPPLY_PASSWORD=<jelszó>
TIPPLY_PUBLISH=1                          # inline publikálás be (0/üres = ki)
TIPPLY_SUBMIT=0                           # 1 = tényleges mentés, különben dry-run
```

## Jóslás

```bash
# Napi entrypoint: a következő 48 óra WC-meccsei → predictions.csv (+ Langfuse, + tipp.ly ha be van kapcsolva)
uv run meccsjoslo

# Tetszőleges órás ablak, választható modellel → predictions_next<N>h.csv
uv run python scripts/predict_window.py 36
uv run python scripts/predict_window.py 48 gemini-3.5-flash

# A 4 beégetett teszteset (ECU–CUW, TUN–JPN, ESP–KSA, BEL–IRN) → predictions_live_<modell>.csv
uv run python scripts/live_predict.py
uv run python scripts/live_predict.py gemini-3.5-flash
```

Kimenet oszlopai (CSV): valószínűségek (hazai/döntetlen/vendég), **egész**
várható gólszám (a Langfuse-logban float marad), FIFA-rang, indoklás. A 3
valószínűség mindig megvan (kalibrálhatóság), odds nélkül.

## tipp.ly publikálás

A jóslat pontos eredmény tippjét böngésző-automatizálással (Playwright + Gemini
locate) felteszi a tipp.ly-ra. **Két kapcsoló** (lásd a különbséget a `CLAUDE.md`-ben):
`TIPPLY_PUBLISH` = fut-e egyáltalán; `TIPPLY_SUBMIT` = el is mentse-e (vagy csak dry-run).

Egyszeri beállítás: a bejelentkezett session a `storage_state.json`-ban (gitignore).

```bash
# Egy meccs próbája — ALAPBÓL DRY-RUN (semmit nem ment), magyar csapatnevekkel
uv run python scripts/tipply_probe.py "Spanyolország" "Szaúd-Arábia" 2 0
uv run python scripts/tipply_probe.py "Belgium" "Irán" 2 1 --overwrite   # meglévő tipp felülírása (dry-run)
uv run python scripts/tipply_probe.py "Belgium" "Irán" 2 1 --submit      # ÉLES mentés

# Egy már megjósolt CSV sorainak publikálása (újrajóslás nélkül) — ALAPBÓL DRY-RUN
uv run python scripts/tipply_publish_csv.py predictions_next48h.csv
uv run python scripts/tipply_publish_csv.py predictions_next48h.csv --submit       # ÉLES mentés
uv run python scripts/tipply_publish_csv.py predictions_next48h.csv --submit --overwrite

# Teljes inline lánc (predikció + publikálás egyben): a .env-ben TIPPLY_PUBLISH=1
TIPPLY_PUBLISH=1 + TIPPLY_SUBMIT=0  → uv run python scripts/predict_window.py 48   # dry-run inline
TIPPLY_PUBLISH=1 + TIPPLY_SUBMIT=1  → uv run python scripts/predict_window.py 48   # éles mentés inline
```

Eredmény-státuszok meccsenként: `submitted` (élesen mentve), `filled` (dry-run,
beírva+ellenőrizve, nem mentve), `skipped` (már volt tipp, nem írta felül),
`needs_human` (pl. `fixture_mismatch` / `low_confidence` / `bot_wall`).

> A csapatnevek a `data/teams_hu.json` (TLA→magyar) szerint mennek; a fixture-guard
> a tipp.ly által kijelzett magyar nevekhez igazítva. Ha `fixture_mismatch` jön egy
> meccsre, az adott nevet ott kell pontosítani.

## Tesztek

```bash
uv run pytest            # teljes készlet (böngésző/hálózat nélkül, mockokkal)
uv run pytest -q tests/test_tipply_flow.py
```

## Ütemezés (cron) — minden reggel 08:00 budapesti idő

`crontab -e`, és tedd be (a `meccsjoslo` entrypoint a napi 48h-s futás, tipp.ly +
ntfy bekötve):

```cron
CRON_TZ=Europe/Budapest
0 8 * * * cd /home/gergo/job/apisport && /home/gergo/.local/bin/uv run meccsjoslo >> /home/gergo/job/apisport/cron.log 2>&1
```

Egyéni ablakhoz a 48h helyett (pl. következő 24h):

```cron
0 8 * * * cd /home/gergo/job/apisport && /home/gergo/.local/bin/uv run python scripts/predict_window.py 24 >> /home/gergo/job/apisport/cron.log 2>&1
```

- `CRON_TZ=Europe/Budapest` → DST-biztos (08:00 helyi idő nyáron-télen is).
- `cd ...` + abszolút `uv` út: a cronnak minimális a PATH-a, és így találja a `.venv`-et.
- A publikáláshoz a `.env`-ben `TIPPLY_PUBLISH=1` kell (és `TIPPLY_SUBMIT=1` az éles mentéshez).

**⚠️ WSL:** a cron nem indul magától. Indítás: `sudo service cron start` (a WSL
leállásakor megáll). Tartós megoldás: systemd a `/etc/wsl.conf`-ban
(`[boot]\nsystemd=true`), majd `sudo systemctl enable --now cron`. A gépnek +
WSL-nek futnia kell 08:00-kor — megbízhatóbb alternatíva a **Windows
Feladatütemező**, ami felébreszti a gépet és elindítja:
`wsl -d <distro> -- bash -lc "cd /home/gergo/job/apisport && /home/gergo/.local/bin/uv run meccsjoslo >> cron.log 2>&1"`.

## Hasznos tudni

- **Idő:** minden UTC-ben (`utcDate`); a futás-ablakot a valós UTC-időhöz méri.
- **Rate limit:** football-data 10 kérés/perc — a kliens 429-re vár és újrapróbál.
- **Langfuse:** az LLM-hívások generation span-ként, token+költséggel; egy futás
  egy session alatt (modellenként szűrhető).
