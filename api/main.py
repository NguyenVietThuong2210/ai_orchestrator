"""FastAPI application entry point."""
from __future__ import annotations

# load_dotenv() MUST run before importing api.routes (which transitively imports
# orchestrator.graph, which reads MAX_QA_ITERATIONS / CHECKPOINT_DB at module level).
from dotenv import load_dotenv
load_dotenv()

import logging
import pathlib
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

_FRONTEND_DIST = pathlib.Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    pathlib.Path(os.getenv("ARTIFACT_DIR", "./artifacts")).mkdir(parents=True, exist_ok=True)
    pathlib.Path("./data").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="AI Orchestrator",
    description="Four-agent pipeline: PM → Analyser → Engineer → QA",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Serve React SPA — only when the production build exists.
# In dev mode (npm run dev), Vite serves on :5173 with its own proxy.
if _FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(request: Request, full_path: str):
        # Serve any file that actually exists in dist/ (favicon, robots.txt, etc.)
        candidate = _FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        # Everything else → index.html (client-side routing)
        return FileResponse(_FRONTEND_DIST / "index.html")
