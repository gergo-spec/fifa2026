# Story 001 — Config és `.env` betöltő

## Cél
A projekt minden konstansa és a titkok egy helyről, a kettőspontos `.env`-ből
és default értékekből töltődjenek.

## Indoklás
A `.env` szokatlan, **kettősponttal** elválasztott formátumú (`KULCS:ÉRTÉK`), és
a `FOOTBALL-DATA-URL` séma/verzió nélküli — ezt központilag kell kezelni, hogy a
node-ok ne ismételjék a parszolást.

## Hatókör
- `config.py`: `load_env(path)` → dict a `.env`-ből (`:` mentén split, `strip`).
- Konstansok a SPECIFICATION 8. szakasza szerint (`FOOTBALL_DATA_BASE`,
  `COMPETITION`, `RECENT_N`, `GEMINI_MODEL`, `HOST_NATIONS`, fájlutak, stb.).
- `football_data_token()`, `gemini_api_key()`, `gemini_model()` getterek.
  A `gemini_model()` a `.env` `GEMINI-MODEL` kulcsát adja, default
  `gemini-3.1-flash-lite`.
- `FOOTBALL_DATA_BASE` = `https://api.football-data.org/v4` (a `.env` host-jából
  séma+`/v4` hozzáfűzve, vagy fix konstans).

## Elfogadási kritériumok
- [ ] `load_env` egy `KULCS:ÉRTÉK` soros fájlból helyes dictet ad, whitespace-t trimmel.
- [ ] A `:` utáni érték is tartalmazhat `:`-t? → split csak az **első** `:`-nél.
- [ ] Hiányzó kulcs kérése beszédes hibát dob (nem `KeyError` nyersen).
- [ ] `FOOTBALL_DATA_BASE` tartalmazza a `https://` sémát és a `/v4`-et.
- [ ] A `.env` soha nincs a kódban; teszt ideiglenes fájlt használ.

## Teszt-ötletek
- tmp `.env` fixture → `load_env` visszaadja a 3 kulcsot.
- Üres/komment sor kihagyása.
- Hiányzó `GEMINI-API-KEY` → beszédes `RuntimeError`.
- Hiányzó `GEMINI-MODEL` → `gemini_model()` a `gemini-3.1-flash-lite` defaultot adja; jelenléte felülírja.
