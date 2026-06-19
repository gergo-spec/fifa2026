"""`predict` node – az LLM (Gemini) jósol.

A jeleket tömör, címkézett összefoglalóvá formázza (nem nyers JSON-dömping), és
**3 valószínűséget + várható gólszámot + 1-2 mondat indoklást** kér. Csoport-
körben a NYERS állást is megkapja, és abból az LLM vezeti le a motivációt.

Tilos odds-ot használni. A három valószínűséget normalizáljuk (összeg ≈ 1.0).
Az LLM-hívás egy `predictor(prompt: str) -> dict` callable mögé van rejtve,
így teszthez mockolható; az éles változat Gemint hív strukturált kimenettel.
"""

from __future__ import annotations

from typing import Callable

from meccsjoslo import config

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
        f"Házigazda-előny: {_fmt(state.get('host_advantage'))}",
        f"Helyszín magassága (m): {_fmt(state.get('venue_altitude_m'))}, "
        f"klíma: {_fmt(state.get('venue_climate'))}",
    ]

    standings = state.get("group_standings")
    if standings:
        lines += [
            "",
            "Csoportállás (NYERS – ebből vezesd le a motivációt: ki jutott már "
            "tovább, kinek nincs tét, kinek kell konkrét gólkülönbség):",
            f"  csoport: {standings.get('group')}",
            f"  hazai sor: {_fmt(standings.get('home_row'))}",
            f"  vendég sor: {_fmt(standings.get('away_row'))}",
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
) -> Callable[[str], dict]:
    """Éles predictor: Gemint hív strukturált kimenettel (nincs unit-teszt – hálózat).

    Ha `langfuse` kliens kapott, minden LLM-hívás egy Langfuse „generation"
    span-ként naplózódik (modell, prompt, válasz)."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    model = model or config.gemini_model()
    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key or config.gemini_api_key(),
        temperature=0.2,
    )

    def predict(prompt: str) -> dict:
        if langfuse is None:
            return _parse_llm_json(llm.invoke(prompt))
        with langfuse.start_as_current_observation(
            name="gemini-predict",
            as_type="generation",
            model=model,
            input=prompt,
            model_parameters={"temperature": 0.2},
        ) as generation:
            resp = llm.invoke(prompt)
            result = _parse_llm_json(resp)
            generation.update(output=result, usage_details=_usage_details(resp))
            return result

    return predict
