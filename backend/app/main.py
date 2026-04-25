from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import ASSET_ROOT
from .datastore import init_store
from .routes import (
    actions,
    advertisers,
    agent,
    campaigns,
    creatives,
    portfolio,
    recommendations,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    init_store()
    yield


app = FastAPI(title="Smadex Creative Intelligence", version="0.1.0", lifespan=lifespan)

# Allow:
#   - http://(localhost|127.0.0.1):<any port>   (local dev)
#   - https://*.vercel.app                       (Vercel preview + prod)
#   - any FRONTEND_ORIGIN env value (e.g. https://smadex.cooking, registered at Porkbun)
import os as _os  # noqa: E402

_extra_origin = _os.environ.get("FRONTEND_ORIGIN", "").rstrip("/")
_origin_regex_parts = [
    r"http://(localhost|127\.0\.0\.1):\d+",
    r"https://[a-zA-Z0-9-]+\.vercel\.app",
]
if _extra_origin:
    import re as _re  # noqa: E402

    _origin_regex_parts.append(_re.escape(_extra_origin))

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex="|".join(f"({p})" for p in _origin_regex_parts),
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=ASSET_ROOT), name="assets")

app.include_router(portfolio.router, prefix="/api", tags=["portfolio"])
app.include_router(creatives.router, prefix="/api", tags=["creatives"])
app.include_router(advertisers.router, prefix="/api", tags=["advertisers"])
app.include_router(campaigns.router, prefix="/api", tags=["campaigns"])
app.include_router(agent.router, prefix="/api", tags=["agent"])
app.include_router(actions.router, prefix="/api", tags=["actions"])
app.include_router(recommendations.router, prefix="/api", tags=["advisor"])


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
