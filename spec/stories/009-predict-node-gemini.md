# Story 009 — `predict` node (Gemini, strukturált kimenet)

## Cél
Az LLM a strukturált jelekből 3 valószínűséget + várható gólszámot + indoklást
ad.

## Indoklás
A jóslást maga az LLM végzi. Mindig 3 valószínűség (kalibrálhatóság), odds
nélkül.

## Hatókör
- `nodes/predict.py`, `langchain-google-genai`, a modell a `config.gemini_model()`-ből
  (a `.env` `GEMINI-MODEL` kulcsa, default `gemini-3.1-flash-lite`).
- A jeleket **tömör, címkézett** összefoglalóvá formázza (nem nyers JSON-dömping):
  ranglista + rank_diff, forma, fáradtság (rest_days, density), gólok,
  házigazda, klíma/magasság, és csoportkörben a **nyers állás** (az LLM vezeti
  le belőle a motivációt).
- **Structured output** (JSON séma): `prob_home`, `prob_draw`, `prob_away`,
  `expected_goals_home`, `expected_goals_away`, `rationale`.
- A 3 valószínűséget **normalizáljuk** (összeg ≈ 1.0).
- Prompt explicit tiltja az odds használatát és a „single tipp"-et.
- Rossz/nem-normalizált válasz → 1× retry szigorúbb prompttal; tartós hiba → jelölt sor.

## Elfogadási kritériumok
- [ ] Mockolt LLM-válaszból a 3 prob + xG + rationale a State-be kerül.
- [ ] A három valószínűség összege normalizálás után ≈ 1.0.
- [ ] Csoportköri meccsnél a nyers állás benne van a promptban.
- [ ] A prompt nem tartalmaz odds-adatot.
- [ ] Hibás LLM-JSON → retry ág tesztelve.

## Teszt-ötletek
- Mock Gemini fix JSON-nal → State assert.
- Nem normalizált probák (0.5/0.4/0.3) → normalizálva 1.0.
- Hibás JSON → retry meghívódik.
