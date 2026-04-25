# Smadex backend

FastAPI service that loads the Smadex dataset into memory and serves the advertiser → campaign → creative hierarchy plus per-creative daily time series.

## Run

```
uv sync
uv run uvicorn app.main:app --reload --port 8001
```

Backend listens on `http://localhost:8001` (port 8000 was already in use on this machine when we scaffolded). Interactive docs at `/docs`. Static PNG assets served under `/assets/`.
