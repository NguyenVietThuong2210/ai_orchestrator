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
from orchestrator.graph import get_app, close_app
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

_FRONTEND_DIST = pathlib.Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    pathlib.Path(os.getenv("ARTIFACT_DIR", "./artifacts")).mkdir(parents=True, exist_ok=True)
    pathlib.Path(os.getenv("PROJECTS_ROOT", "./projects")).mkdir(parents=True, exist_ok=True)
    await get_app()   # connect to Postgres + compile graph at startup
    yield
    await close_app()


app = FastAPI(
    title="AI Orchestrator",
    description="Eight-agent pipeline: PM → Analyser → Engineer → Reviewer → Security → QA → Deploy → Retrospective",
    version="0.1.0",
    lifespan=lifespan,
)

_CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:8000",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["api", "orchestrator", "agents", "mcp_server"],
    )
