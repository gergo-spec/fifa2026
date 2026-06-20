"""tipp.ly futás-konfiguráció (csak pydantic; titkok SecretStr-ben maszkolva)."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, SecretStr


class TipplyConfig(BaseModel):
    email: str
    password: SecretStr
    base_url: str = "https://tipp.ly"
    storage_state_path: Path = Path("storage_state.json")

    @property
    def bets_url(self) -> str:
        return f"{self.base_url}/hu/bets"

    @property
    def login_url(self) -> str:
        return f"{self.base_url}/hu/login"
