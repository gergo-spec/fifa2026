"""Konfiguráció és `.env` betöltő.

A `.env` **kettősponttal** elválasztott (`KULCS:ÉRTÉK`), és a
`FOOTBALL-DATA-URL` séma/verzió nélküli — ezt itt központilag kezeljük, hogy a
node-ok ne ismételjék a parszolást.
"""

from __future__ import annotations

from pathlib import Path

# A projektgyökér: .../apisport (a src/meccsjoslo/config.py-ból két szint fel).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"

# --- konstansok (SPECIFICATION 8.) -----------------------------------------
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"
COMPETITION = "WC"
RECENT_N = 5
FORM_WINDOW_DAYS = 14
DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"
HOST_NATIONS = frozenset({"USA", "MEX", "CAN"})

RANKING_FILE = PROJECT_ROOT / "data" / "fifa_ranking_2026-06-11.json"
VENUES_FILE = PROJECT_ROOT / "data" / "venues.json"
OUTPUT_CSV = PROJECT_ROOT / "predictions.csv"
RATE_LIMIT_SLEEP_S = 6


def load_env(path: Path | str = DEFAULT_ENV_PATH) -> dict[str, str]:
    """A `.env` betöltése dictbe.

    Üres és `#`-kommentsorok kihagyva. A határoló az első `:` VAGY `=` a sorban
    (amelyik előbb jön) – így a vegyes `.env` (football-data `:`, Langfuse/Gemini
    `=`) is működik. A kulcsnévben nincs határoló, ezért az első előfordulás
    mindig a valódi elválasztó. Az érték körüli idézőjeleket levágjuk.
    """
    cfg: dict[str, str] = {}
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        positions = [pos for pos in (line.find(":"), line.find("=")) if pos != -1]
        if not positions:
            continue
        idx = min(positions)
        key = line[:idx].strip()
        value = line[idx + 1:].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        cfg[key] = value
    return cfg


def _require(cfg: dict[str, str], key: str) -> str:
    try:
        return cfg[key]
    except KeyError:
        raise RuntimeError(
            f"Hiányzó kulcs a .env-ben: {key!r}. "
            f"Vesd össze a .env.example-lel."
        ) from None


def _resolve(cfg: dict[str, str] | None) -> dict[str, str]:
    return cfg if cfg is not None else load_env()


def football_data_token(cfg: dict[str, str] | None = None) -> str:
    return _require(_resolve(cfg), "FOOTBALL-DATA-API-KEY")


def gemini_api_key(cfg: dict[str, str] | None = None) -> str:
    return _require(_resolve(cfg), "GEMINI-API-KEY")


def gemini_model(cfg: dict[str, str] | None = None) -> str:
    """A `.env` `GEMINI-MODEL` kulcsa, vagy a default `gemini-3.1-flash-lite`."""
    return _resolve(cfg).get("GEMINI-MODEL", DEFAULT_GEMINI_MODEL)


def langfuse_client(cfg: dict[str, str] | None = None):
    """Langfuse kliens a `.env`-ből, vagy `None`, ha nincs konfigurálva.

    Kulcsok: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`.
    """
    cfg = _resolve(cfg)
    public = cfg.get("LANGFUSE_PUBLIC_KEY")
    secret = cfg.get("LANGFUSE_SECRET_KEY")
    if not (public and secret):
        return None
    from langfuse import Langfuse

    return Langfuse(
        public_key=public,
        secret_key=secret,
        base_url=cfg.get("LANGFUSE_BASE_URL"),
    )
