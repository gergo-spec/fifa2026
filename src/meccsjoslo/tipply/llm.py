"""Locate LLM – prompt + strukturált kimenet (LocatePlan).

A konkrét kliens a meglévő **langchain-google-genai** SDK-t használja
(`with_structured_output(LocatePlan)`), így az egész projektben egy Gemini SDK
van. A unit tesztek a locate node-ot egy fake `LlmClient`-en keresztül hajtják.
"""

from __future__ import annotations

from typing import Protocol

from meccsjoslo.tipply.state import LocatePlan, Match, Score

ACTION_VOCABULARY = ("fill", "click", "select")


class LlmClient(Protocol):
    async def locate(self, prompt: str) -> object:
        """A modell strukturált válasza (LocatePlan, dict vagy JSON-string)."""
        ...


def build_locate_prompt(match: Match, score: Score, snapshot: str) -> str:
    """A locate prompt összeállítása. Titkot nem tartalmaz."""
    return (
        "You locate a football match on a dynamic betting page and target its two "
        "goal inputs. The page is dynamic (knockout fixtures unknown), and team names "
        "may be fuzzy, localized, or abbreviated — resolve them to the correct row.\n\n"
        f"Target match: home={match.home!r} vs away={match.away!r}\n"
        f"Predicted exact score: {score.home_goals}-{score.away_goals} "
        f"({match.home}={score.home_goals}, {match.away}={score.away_goals})\n\n"
        "Cleaned page snapshot:\n"
        f"{snapshot}\n\n"
        f"Allowed actions: {', '.join(ACTION_VOCABULARY)}.\n"
        "The snapshot is usually JSON: {\"fixtures\":[{\"home\",\"away\","
        "\"home_input\",\"away_input\"}]}, where home_input/away_input are the exact "
        "name attributes of the two goal inputs. Match the target by team names (resolve "
        "fuzzy/localized/abbreviated forms) and return TWO fill actions: home goals into "
        "home_input, away goals into away_input.\n"
        "BOTH teams must belong to the SAME fixture. If no fixture lists both the requested "
        "home and away teams together, do NOT guess a partial match — return an empty actions "
        "list with confidence 0 and a rationale that no fixture matches.\n"
        "Locator strategy: anchor on the stable input name with a css locator like "
        "css value `input[name='<home_input>']`. (If the snapshot is instead an accessibility "
        "tree, prefer role/text/label over brittle deep css or xpath.)\n"
        "Include a confidence in [0,1] and a short rationale."
    )


class LangchainLocateLLM:
    """Locate LLM a langchain-google-genai-val, LocatePlan strukturált kimenettel.

    Integrációs határ – élesben hívja a Gemint, unit tesztben nem.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None):
        from langchain_google_genai import ChatGoogleGenerativeAI

        from meccsjoslo import config

        llm = ChatGoogleGenerativeAI(
            model=model or config.gemini_model(),
            google_api_key=api_key or config.gemini_api_key(),
            temperature=0.0,
        )
        self._structured = llm.with_structured_output(LocatePlan)

    async def locate(self, prompt: str) -> LocatePlan:
        return await self._structured.ainvoke(prompt)
