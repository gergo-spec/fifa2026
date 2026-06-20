"""Snapshot-tisztítás – az LLM nézete a lapról legyen kicsi és hasznos.

Az ARIA snapshot / fixtures JSON méretét korlátozzuk, hogy egy nagy lap se
fújja fel a promptot. Tiszta függvény, böngésző nélkül tesztelhető.
"""

from __future__ import annotations

DEFAULT_MAX_CHARS = 12000


def clamp_snapshot(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Túl nagy snapshot levágása, látható jelzéssel arról, mennyit vágtunk."""
    if len(text) <= max_chars:
        return text
    cut = len(text) - max_chars
    return f"{text[:max_chars]}\n… [truncated {cut} chars]"
