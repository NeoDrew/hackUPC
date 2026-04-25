# Smadex backend

FastAPI service that loads the Smadex dataset into memory and serves the advertiser → campaign → creative hierarchy plus per-creative daily time series.

## Run

```
uv sync
uv run uvicorn app.main:app --reload --port 8001
```

Backend listens on `http://localhost:8001` (port 8000 was already in use on this machine when we scaffolded). Interactive docs at `/docs`. Static PNG assets served under `/assets/`.

## Vision Insight (Gemma 4)

The Twin Comparison page generates its Vision Insight via Gemma 4 on Google AI Studio. Set `GEMINI_API_KEY` in `backend/.env` (gitignored) — grab a key from <https://aistudio.google.com/apikey>.

```
GEMINI_API_KEY=...your-key...
# Optional override if Google promotes a newer Gemma model id
# VISION_INSIGHT_MODEL=gemma-3-27b-it
```

If the key is missing or the API errors, the backend falls back to canned templates and stamps `is_stub: true` on the response — the UI then shows a `[preview]` chip on the Vision Insight card.
