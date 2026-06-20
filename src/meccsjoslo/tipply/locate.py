"""Locate node – LLM-in-the-loop: a meccs megtalálása a dinamikus /hu/bets lapon."""

from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError

from meccsjoslo.tipply.llm import build_locate_prompt
from meccsjoslo.tipply.state import LocatePlan, Match, Score


class LocateError(RuntimeError):
    """Az LLM a korláton belül nem adott séma-érvényes tervet."""


async def locate_match(
    llm,
    *,
    match: Match,
    score: Score,
    snapshot: str,
    max_attempts: int = 2,
) -> LocatePlan:
    """Action-tervet kér az LLM-től, és a séma ellen validálja.

    Érvénytelen kimenetnél legfeljebb ``max_attempts`` LLM-körig újrapróbál,
    majd megáll – a ciklus korlátos.
    """
    base_prompt = build_locate_prompt(match, score, snapshot)
    prompt = base_prompt
    last_error: Exception | None = None

    for _ in range(max_attempts):
        raw = await llm.locate(prompt)
        try:
            return LocatePlan.model_validate(_as_payload(raw))
        except (ValidationError, ValueError) as err:
            last_error = err
            prompt = (
                f"{base_prompt}\n\nYour previous answer was invalid: {err}\n"
                "Return JSON that matches the schema exactly."
            )

    raise LocateError(f"no schema-valid plan after {max_attempts} attempt(s)") from last_error


def _as_payload(raw: object) -> object:
    # A langchain strukturált kimenet közvetlenül LocatePlan-t adhat vissza.
    if isinstance(raw, BaseModel):
        return raw.model_dump()
    if isinstance(raw, str):
        return json.loads(raw)
    return raw
