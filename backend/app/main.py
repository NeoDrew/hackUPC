from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import ASSET_ROOT, CORS_ORIGINS
from .datastore import init_store
from .routes import advertisers, campaigns, creatives, portfolio

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    init_store()
    yield


app = FastAPI(title="Smadex Creative Intelligence", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=ASSET_ROOT), name="assets")

app.include_router(portfolio.router, prefix="/api", tags=["portfolio"])
app.include_router(creatives.router, prefix="/api", tags=["creatives"])
app.include_router(advertisers.router, prefix="/api", tags=["advertisers"])
app.include_router(campaigns.router, prefix="/api", tags=["campaigns"])


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
