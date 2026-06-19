# Meccsjósló

LangGraph alapú alkalmazás, ami egy le nem játszott labdarúgó-meccs kimenetét
jósolja meg LLM-mel (Gemini). Részletek: [`CLAUDE.md`](CLAUDE.md) és
[`SPECIFICATION.md`](SPECIFICATION.md).

## Indulás

```bash
uv sync                 # függőségek telepítése (.venv)
uv run meccsjoslo       # napi futás: következő 48h WC-meccsek → CSV
uv run pytest           # tesztek
```

A titkokat a `.env` tartalmazza (lásd `.env.example`).
