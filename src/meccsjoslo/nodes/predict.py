"""`predict` node – az LLM (Gemini) jósol.

A jeleket tömör, címkézett összefoglalóvá formázza (nem nyers JSON-dömping), és
**3 valószínűséget + várható gólszámot + 1-2 mondat indoklást** kér. Csoport-
körben a NYERS állást is megkapja, és abból az LLM vezeti le a motivációt.

Tilos odds-ot használni. A három valószínűséget normalizáljuk (összeg ≈ 1.0).
Az LLM-hívás egy `predictor(prompt: str) -> dict` callable mögé van rejtve,
így teszthez mockolható; az éles változat Gemint hív strukturált kimenettel.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from meccsjoslo import config

_LOG = logging.getLogger(__name__)

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_RETRY_BACKOFF_SECONDS: tuple[float, ...] = (30.0, 60.0, 120.0, 180.0, 300.0, 600.0)


def _invoke_with_retry(
    invoke: Callable[[str], object],
    prompt: str,
    *,
    backoff: tuple[float, ...] = _RETRY_BACKOFF_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> object:
    """`invoke(prompt)` átmeneti Gemini-szerverhibánál backoff-fal újrapróbálva.

    Csak `_RETRYABLE_STATUS` státuszú `google.genai` hibát próbál újra; egyébként
    (és a backoff kimerülése után) az eredeti kivételt dobja tovább. A `sleep`
    injektálható teszthez."""
    from google.genai.errors import APIError

    for attempt, wait in enumerate((*backoff, None)):
        try:
            return invoke(prompt)
        except APIError as exc:
            status = getattr(exc, "code", None)
            if status not in _RETRYABLE_STATUS or wait is None:
                raise
            _LOG.warning(
                "Gemini HTTP %s – újrapróba %d/%d %.0f mp múlva…",
                status, attempt + 1, len(backoff), wait,
            )
            sleep(wait)
    raise AssertionError("elérhetetlen ág")

_REQUIRED_NUMERIC = (
    "prob_home",
    "prob_draw",
    "prob_away",
    "expected_goals_home",
    "expected_goals_away",
)

_STRICT_SUFFIX = (
    "\n\nFONTOS: KIZÁRÓLAG érvényes JSON-t adj vissza, ezekkel a kulcsokkal: "
    "prob_home, prob_draw, prob_away (0 és 1 közötti számok, az összegük ~1), "
    "expected_goals_home, expected_goals_away (nemnegatív számok), rationale "
    "(rövid szöveg). Semmi mást."
)


def _fmt(value) -> str:
    return "n/a" if value is None else str(value)


def _fmt_recent(matches: list | None) -> str:
    """Az utolsó N meccs tömör listája (frissebb elöl)."""
    if not matches:
        return "nincs adat"
    parts = []
    for m in matches[:5]:
        parts.append(
            f"{m['utcDate'][:10]} {m['result']} "
            f"{m['goals_for']}-{m['goals_against']} vs {m['opponent_tla']} ({m['side']})"
        )
    return "; ".join(parts)


def _fmt_h2h(h2h: dict | None) -> str | None:
    """Egymás elleni mérleg tömör összegzése.

    Kezeli a fizetős `aggregates` (győzelem-mérleg) és a free tier
    `resultSet` + `matches` formátumot is; 0 találkozónál ezt jelzi.
    """
    if not h2h:
        return None
    agg = h2h.get("aggregates") or {}
    matches = h2h.get("matches") or []
    count = agg.get("numberOfMatches")
    if count is None:
        count = (h2h.get("resultSet") or {}).get("count", len(matches))
    if not count:
        return "nincs korábbi találkozó"

    home, away = agg.get("homeTeam") or {}, agg.get("awayTeam") or {}
    if home.get("wins") is not None:
        return (
            f"{count} meccs, hazai gy {home.get('wins')} / "
            f"döntetlen {home.get('draws')} / vendég gy {away.get('wins')}"
        )
    meetings = []
    for m in matches[:3]:
        full = m.get("score", {}).get("fullTime", {})
        meetings.append(
            f"{m.get('utcDate', '')[:10]} {m['homeTeam'].get('tla', '?')} "
            f"{full.get('home', '?')}-{full.get('away', '?')} {m['awayTeam'].get('tla', '?')}"
        )
    return f"{count} korábbi meccs" + (": " + "; ".join(meetings) if meetings else "")


def _fmt_row(row: dict | None) -> str:
    """Egy csapat tabella-sora tömören (a nyers dict / címer-URL nélkül)."""
    if not row:
        return "n/a"
    team = row.get("team", {})
    return (
        f"{team.get('tla', '?')}: {row.get('position')}. hely, {row.get('points')}p, "
        f"GK {row.get('goalDifference')} ({row.get('goalsFor')}-{row.get('goalsAgainst')}), "
        f"Gy{row.get('won')}-D{row.get('draw')}-V{row.get('lost')}"
    )


def _fmt_standings_table(standings: dict) -> list[str]:
    """A teljes csoporttabella soronként (motiváció-kontextushoz)."""
    rows = []
    for r in standings.get("table") or []:
        team = r.get("team", {})
        rows.append(
            f"{r.get('position')}. {team.get('tla', '?')} {r.get('points')}p "
            f"GK{r.get('goalDifference')} (J{r.get('playedGames')})"
        )
    return rows


def build_prompt(state: dict) -> str:
    """Strukturált, címkézett prompt a jelekből (odds NÉLKÜL)."""
    lines = [
        "Egy le nem játszott labdarúgó VB-meccs kimenetét kell megjósolnod a "
        "lenti jelekből. NE használj fogadóirodai adatot. Mindig HÁROM "
        "valószínűséget adj (hazai/döntetlen/vendég), sosem egyetlen tippet.",
        "",
        f"Meccs: {state.get('home_name')} (hazai) vs {state.get('away_name')} (vendég)",
        f"Szakasz: {state.get('stage')}  Csoport: {_fmt(state.get('group'))}",
        "",
        "FIFA-ranglista:",
        f"  hazai #{_fmt(state.get('home_rank'))}, vendég #{_fmt(state.get('away_rank'))}, "
        f"helyezéskülönbség (vendég-hazai): {_fmt(state.get('rank_diff'))}",
        "Forma (frissebb meccs nagyobb súllyal, 0-1):",
        f"  hazai: {_fmt(state.get('home_form'))}",
        f"  vendég: {_fmt(state.get('away_form'))}",
        "Gólok (lőtt=attack, kapott=defense átlag):",
        f"  hazai: {_fmt(state.get('home_goals'))}",
        f"  vendég: {_fmt(state.get('away_goals'))}",
        "Fáradtság (pihenőnapok, meccssűrűség):",
        f"  hazai: {_fmt(state.get('home_fatigue'))}",
        f"  vendég: {_fmt(state.get('away_fatigue'))}",
        "Utolsó meccsek (frissebb elöl, eredmény + gólok + ellenfél):",
        f"  hazai: {_fmt_recent(state.get('home_recent_matches'))}",
        f"  vendég: {_fmt_recent(state.get('away_recent_matches'))}",
        f"Házigazda-előny: {_fmt(state.get('host_advantage'))}",
        f"Helyszín magassága (m): {_fmt(state.get('venue_altitude_m'))}, "
        f"klíma: {_fmt(state.get('venue_climate'))}",
    ]

    h2h = _fmt_h2h(state.get("h2h"))
    if h2h:
        lines.append(f"Egymás elleni mérleg (H2H): {h2h}")

    standings = state.get("group_standings")
    if standings:
        lines += [
            "",
            "Csoportállás (NYERS – ebből vezesd le a motivációt: ki jutott már "
            "tovább, kinek nincs tét, kinek kell konkrét gólkülönbség):",
            f"  csoport: {standings.get('group')}",
        ]
        lines += [f"  {row}" for row in _fmt_standings_table(standings)]
        lines += [
            f"  hazai sor: {_fmt_row(standings.get('home_row'))}",
            f"  vendég sor: {_fmt_row(standings.get('away_row'))}",
        ]

    lines += [
        "",
        "Válaszolj JSON-nal: prob_home, prob_draw, prob_away (összeg ~1), "
        "expected_goals_home, expected_goals_away, rationale (1-2 mondat).",
    ]
    return "\n".join(lines)


def _is_valid(raw) -> bool:
    if not isinstance(raw, dict):
        return False
    try:
        values = [float(raw[k]) for k in _REQUIRED_NUMERIC]
    except (KeyError, TypeError, ValueError):
        return False
    if any(v < 0 for v in values):
        return False
    if raw.get("rationale") in (None, ""):
        return False
    # a három valószínűség összege nem lehet nulla (normalizálhatatlan)
    return (float(raw["prob_home"]) + float(raw["prob_draw"]) + float(raw["prob_away"])) > 0


def make_predict(predictor: Callable[[str], dict]):
    def predict(state: dict) -> dict:
        prompt = build_prompt(state)
        raw = predictor(prompt)
        if not _is_valid(raw):
            raw = predictor(prompt + _STRICT_SUFFIX)  # pontosan egy újrapróba
        if not _is_valid(raw):
            raise RuntimeError(
                "a predikciós LLM nem adott érvényes választ (újrapróba után sem)"
            )

        ph, pd, pa = (float(raw["prob_home"]), float(raw["prob_draw"]), float(raw["prob_away"]))
        total = ph + pd + pa
        return {
            "prob_home": round(ph / total, 4),
            "prob_draw": round(pd / total, 4),
            "prob_away": round(pa / total, 4),
            "expected_goals_home": float(raw["expected_goals_home"]),
            "expected_goals_away": float(raw["expected_goals_away"]),
            "rationale": str(raw["rationale"]),
        }

    return predict


def _usage_details(resp) -> dict | None:
    """Token-felhasználás kiolvasása a LangChain válaszból Langfuse-formátumban."""
    usage = getattr(resp, "usage_metadata", None) or {}
    if not usage:
        return None
    details: dict[str, int] = {}
    if usage.get("input_tokens") is not None:
        details["input"] = usage["input_tokens"]
    if usage.get("output_tokens") is not None:
        details["output"] = usage["output_tokens"]
    if usage.get("total_tokens") is not None:
        details["total"] = usage["total_tokens"]
    return details or None


def _parse_llm_json(resp) -> dict:
    import json

    content = getattr(resp, "content", resp)
    # a Gemini a content-et listányi rész-blokkban is adhatja
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    text = str(content).strip()
    # a JSON-objektum kivágása (esetleges ```json fence / kísérőszöveg mellől)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


def gemini_predictor(
    model: str | None = None,
    api_key: str | None = None,
    langfuse=None,
    fallback_model: str | None = None,
) -> Callable[[str], dict]:
    """Éles predictor: Gemint hív strukturált kimenettel (nincs unit-teszt – hálózat).

    Ha `langfuse` kliens kapott, minden LLM-hívás egy Langfuse „generation"
    span-ként naplózódik (modell, prompt, válasz). Ha `fallback_model` adott és
    az elsődleges modell kimerítette a retry-ket, a tartalék modellre vált."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    model = model or config.gemini_model()
    api_key = api_key or config.gemini_api_key()
    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0.2,
    )

    def _call(llm_instance, model_name, prompt):
        if langfuse is None:
            return _parse_llm_json(_invoke_with_retry(llm_instance.invoke, prompt))
        with langfuse.start_as_current_observation(
            name="gemini-predict",
            as_type="generation",
            model=model_name,
            input=prompt,
            model_parameters={"temperature": 0.2},
        ) as generation:
            resp = _invoke_with_retry(llm_instance.invoke, prompt)
            result = _parse_llm_json(resp)
            generation.update(output=result, usage_details=_usage_details(resp))
            return result

    def predict(prompt: str) -> dict:
        from google.genai.errors import APIError

        try:
            return _call(llm, model, prompt)
        except APIError as exc:
            status = getattr(exc, "code", None)
            if not fallback_model or fallback_model == model or status not in _RETRYABLE_STATUS:
                raise
            _LOG.warning(
                "Elsődleges modell (%s) kimerült – fallback: %s",
                model, fallback_model,
            )
            fb_llm = ChatGoogleGenerativeAI(
                model=fallback_model,
                google_api_key=api_key,
                temperature=0.2,
            )
            return _call(fb_llm, fallback_model, prompt)

    return predict
