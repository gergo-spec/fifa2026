"""Story 001 – config és .env betöltő."""

import pytest

from meccsjoslo import config


def _write_env(tmp_path, text):
    p = tmp_path / ".env"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_env_parses_colon_separated(tmp_path):
    p = _write_env(
        tmp_path,
        "FOOTBALL-DATA-API-KEY:  abc123 \n"
        "FOOTBALL-DATA-URL:football-data.org\n"
        "GEMINI-API-KEY:secret\n",
    )
    cfg = config.load_env(p)
    assert cfg["FOOTBALL-DATA-API-KEY"] == "abc123"
    assert cfg["FOOTBALL-DATA-URL"] == "football-data.org"
    assert cfg["GEMINI-API-KEY"] == "secret"


def test_load_env_skips_blank_and_comment_lines(tmp_path):
    p = _write_env(tmp_path, "\n# komment\nGEMINI-API-KEY:x\n")
    cfg = config.load_env(p)
    assert cfg == {"GEMINI-API-KEY": "x"}


def test_load_env_splits_only_on_first_colon(tmp_path):
    # az érték tartalmazhat kettőspontot (pl. teljes URL)
    p = _write_env(tmp_path, "FOOTBALL-DATA-URL:https://api.football-data.org/v4\n")
    cfg = config.load_env(p)
    assert cfg["FOOTBALL-DATA-URL"] == "https://api.football-data.org/v4"


def test_load_env_accepts_equals_separator(tmp_path):
    # vegyes .env: a Langfuse/Gemini sorok '='-rel jönnek
    p = _write_env(tmp_path, "GEMINI-API-KEY=AIzaSecret\n")
    cfg = config.load_env(p)
    assert cfg["GEMINI-API-KEY"] == "AIzaSecret"


def test_load_env_uses_earliest_separator(tmp_path):
    # '=' a kulcs után, de ':' a value-ban (URL) → az '='-nél kell hasítani
    p = _write_env(tmp_path, "BASE=https://example.com:8080/x\n")
    cfg = config.load_env(p)
    assert cfg["BASE"] == "https://example.com:8080/x"


def test_load_env_strips_surrounding_quotes(tmp_path):
    p = _write_env(tmp_path, 'TOK="abc123"\n')
    cfg = config.load_env(p)
    assert cfg["TOK"] == "abc123"


def test_getters_read_values(tmp_path):
    p = _write_env(
        tmp_path,
        "FOOTBALL-DATA-API-KEY:tok\nGEMINI-API-KEY:gk\nGEMINI-MODEL:custom-model\n",
    )
    cfg = config.load_env(p)
    assert config.football_data_token(cfg) == "tok"
    assert config.gemini_api_key(cfg) == "gk"
    assert config.gemini_model(cfg) == "custom-model"


def test_gemini_model_defaults_when_absent(tmp_path):
    cfg = config.load_env(_write_env(tmp_path, "GEMINI-API-KEY:gk\n"))
    assert config.gemini_model(cfg) == "gemini-3.1-flash-lite"


def test_missing_required_key_raises_helpful_error(tmp_path):
    cfg = config.load_env(_write_env(tmp_path, "GEMINI-API-KEY:gk\n"))
    with pytest.raises(RuntimeError, match="FOOTBALL-DATA-API-KEY"):
        config.football_data_token(cfg)


def test_base_url_has_scheme_and_version():
    assert config.FOOTBALL_DATA_BASE.startswith("https://")
    assert config.FOOTBALL_DATA_BASE.endswith("/v4")


def test_host_nations_are_the_three_co_hosts():
    assert config.HOST_NATIONS == frozenset({"USA", "MEX", "CAN"})


def test_langfuse_client_none_when_keys_absent(tmp_path):
    cfg = config.load_env(_write_env(tmp_path, "GEMINI-API-KEY:gk\n"))
    assert config.langfuse_client(cfg) is None
