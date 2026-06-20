"""Pydantic state és action sémák a tipp.ly publikáláshoz.

Az ``Action`` szótár és a ``LocatePlan`` a locate-LLM strukturált kimeneti
szerződése.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Match(BaseModel):
    """Cél meccs. A csapatnevek lehetnek fuzzy/lokalizált/rövidített formák."""

    home: str
    away: str


class Score(BaseModel):
    """Megjósolt pontos eredmény."""

    home_goals: int = Field(ge=0)
    away_goals: int = Field(ge=0)


LocatorStrategy = Literal["role", "text", "label", "placeholder", "css", "xpath"]
ROBUST_STRATEGIES: frozenset[str] = frozenset({"role", "text", "label", "placeholder"})


class Locator(BaseModel):
    strategy: LocatorStrategy
    value: str
    name: str | None = None

    @property
    def is_robust(self) -> bool:
        return self.strategy in ROBUST_STRATEGIES


class Action(BaseModel):
    kind: Literal["fill", "click", "select"]
    locator: Locator
    value: str | None = None

    @model_validator(mode="after")
    def _value_required_for_fill_select(self) -> "Action":
        if self.kind in ("fill", "select") and self.value is None:
            raise ValueError(f"action kind={self.kind!r} requires a value")
        return self


class LocatePlan(BaseModel):
    """Az LLM strukturált válasza a meccs megtalálására/megcélzására."""

    actions: list[Action]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = ""


class VerifyResult(BaseModel):
    """A kitöltött gól-inputok visszaolvasása, a kitöltötthöz hasonlítva."""

    ok: bool
    readback: dict[str, dict[str, str | None]]


Status = Literal["filled", "submitted", "skipped", "needs_human", "no_match"]


class FillReport(BaseModel):
    """Egy fill-módú futás eredménye (dry-run a submit előtt megáll)."""

    status: Status
    confidence: float = 0.0
    verify: VerifyResult | None = None
    plan: LocatePlan | None = None
    screenshot: str | None = None
    reason: str | None = None
