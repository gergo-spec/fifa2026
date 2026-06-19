# Story 005 — `derive_features`: forma, fáradtság, gólok

## Cél
A nyers meccsekből három determinisztikus jel mindkét csapatra.

## Indoklás
Az LLM strukturált jeleket kapjon, ne nyers meccslistát — kalibrálhatóság.

## Hatókör
- `nodes/derive_features.py`.
- **forma** (`*_form`): utolsó max 5 meccs → pont (W=3, D=1, L=0),
  **frissebb nagyobb súllyal** (lineáris vagy exponenciális súly),
  normalizált [0,1] + győzelmi arány.
- **fáradtság** (`*_fatigue`): `rest_days` = `utc_date − utolsó meccs dátuma`
  (nap); `matches_in_window` = meccsek száma az utolsó `FORM_WINDOW_DAYS` napban.
  **Utazási távolság NINCS.**
- **gólok** (`*_goals`): `attack` = lőtt gólátlag, `defense` = kapott gólátlag.
- Kevés adat (0–1 meccs) → `insufficient: true` jelzés, ne dobjon hibát.

## Elfogadási kritériumok
- [ ] Ismert meccssorozatra a súlyozott forma kézzel kiszámolt értékkel egyezik.
- [ ] `rest_days` helyes a `utc_date` és az utolsó meccs között.
- [ ] `matches_in_window` az ablakon belüli meccseket számolja.
- [ ] Gólátlagok helyesek (lőtt/kapott).
- [ ] 0 meccs → `insufficient` jel, nincs ZeroDivision.

## Teszt-ötletek
- 5 meccs ismert eredménnyel → forma, gólátlag assert.
- 2 meccs 3 ill. 10 napja → `rest_days`, `matches_in_window`.
- Üres lista → `insufficient`.
