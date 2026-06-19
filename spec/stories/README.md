# Story-k — Meccsjósló (TDD sorrend)

Minden story red → green → refactor ciklussal valósul meg (`/tdd`). A sorrend
függőség-helyes: alulról építkezik (config → kliens → node-ok → gráf →
entrypoint).

| # | Story | Réteg |
|---|---|---|
| 001 | Config és `.env` betöltő | alap |
| 002 | football-data.org v4 kliens | alap |
| 003 | `get_rankings` node | node |
| 004 | `get_previous_matches` node | node |
| 005 | `derive_features`: forma, fáradtság, gólok | node |
| 006 | Venue-jelek: házigazda, klíma, magasság | node + adat |
| 007 | `get_group_standings` node | node |
| 008 | Gráf összeállítás + feltételes elágazás | gráf |
| 009 | `predict` node (Gemini, strukturált) | node |
| 010 | CSV-naplózás + napi entrypoint | integráció |

## Külön adatfeladatok (nem kód-story)
- `data/venues.json` feltöltése a 16 valós VB-helyszínnel (Story 006-hoz).
- A FIFA-ranglista JSON cseréje a 2026-07-20-i frissítéskor.

## Backlog (v1 után)
- Utazási távolság / úti-pihenő különbség (haversine, venue-koordináták).
- Egymás elleni mérleg (H2H) külön súlyként.
- Verseny szerinti súlyozás a formában (barátságos kisebb súly).
- `evaluate` node + Brier-score — **másik repó** tooljaként készül.
