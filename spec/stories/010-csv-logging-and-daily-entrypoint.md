# Story 010 — CSV-naplózás + napi entrypoint

## Cél
A következő 48 óra WC-meccseit végigjósolni és CSV-be naplózni.

## Indoklás
Napi cron/agent-core futás. A CSV-t később külön repó tool értékeli ki
(Brier) — a séma stabil.

## Hatókör
- `logging_csv.py`: `append_prediction(row, path)` — fejléc egyszer, stabil
  oszlopsorrend (SPECIFICATION 7.), tizedes pont, UTF-8, idézőjelezett rationale.
- `main.py`:
  1. config + FIFA JSON + venues betöltés.
  2. `matches(dateFrom=ma, dateTo=ma+2)` → pontos 48h szűrés `utcDate`-tel,
     `status` SCHEDULED/TIMED.
  3. meccsenként `build_graph()` futtatás.
  4. eredmény → `append_prediction`.
  5. football-data hívások közt `RATE_LIMIT_SLEEP_S` szünet.
- Idempotencia v1: append + `run_date` oszlop (dedup a kiértékelő tool dolga).

## Elfogadási kritériumok
- [ ] A 48h ablakon kívüli meccs kimarad (pontos `utcDate` szűrés).
- [ ] A CSV fejléce egyszer íródik, az oszlopsorrend a specifikáció szerinti.
- [ ] Több meccs → több sor, mind a `run_date`-tel.
- [ ] A rate-limit szünet meghívódik a hívások közt (mockolt idő).
- [ ] Teljes futás mockolt API + LLM mellett → várt CSV-tartalom.

## Teszt-ötletek
- 3 meccs (2 ablakban, 1 kívül) → 2 CSV-sor.
- Üres CSV → fejléc + sor; meglévő CSV → csak sor.
- End-to-end mock: matches + graph + csv assert.
