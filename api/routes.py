"""
FastAPI routes:
  POST /run-pipeline      — start pipeline
  POST /approve-spec      — resume after Human Gate
  GET  /status/{job_id}   — poll job state
  GET  /stream/{job_id}   — SSE live event stream
  POST /cancel/{job_id}   — cancel job (best-effort)
"""
from __future__ import annotations

import asyncio
import json
import logging
from functools import lru_cache
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from uuid import uuid4

from api.schemas import (
    RunPipelineRequest, RunPipelineResponse,
    ApproveSpecRequest, ApproveSpecResponse,
    JobStatusResponse, CancelJobResponse,
)
from orchestrator.runner import run_pipeline, resume_pipeline
from orchestrator.graph import compile_app

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory job registry — replace with DB in production
_jobs: dict[str, dict] = {}


@lru_cache(maxsize=1)
def _get_app():
    """Compile LangGraph app once and cache — avoids creating a new SQLite
    connection on every request."""
    return compile_app()


@router.post("/run-pipeline", response_model=RunPipelineResponse)
async def start_pipeline(req: RunPipelineRequest, bg: BackgroundTasks):
    job_id = req.job_id or str(uuid4())
    _jobs[job_id] = {"status": "started", "job_id": job_id}

    async def _run():
        try:
            final = await run_pipeline(req.requirement, job_id=job_id)
            _jobs[job_id].update(final)
        except Exception as exc:
            logger.exception("Pipeline error job_id=%s", job_id)
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"]  = str(exc)

    bg.add_task(_run)
    return RunPipelineResponse(
        job_id=job_id,
        status="started",
        message=f"Pipeline started. Poll GET /status/{job_id} or stream GET /stream/{job_id}",
    )


@router.post("/approve-spec", response_model=ApproveSpecResponse)
async def approve_spec(req: ApproveSpecRequest, bg: BackgroundTasks):
    if req.job_id not in _jobs:
        raise HTTPException(404, f"job_id {req.job_id!r} not found")

    async def _resume():
        try:
            final = await resume_pipeline(req.job_id, decision=req.decision)
            _jobs[req.job_id].update(final)
        except Exception as exc:
            logger.exception("Resume error job_id=%s", req.job_id)
            _jobs[req.job_id]["status"] = "failed"
            _jobs[req.job_id]["error"]  = str(exc)

    bg.add_task(_resume)
    return ApproveSpecResponse(
        job_id=req.job_id,
        status="resuming",
        message=f"Pipeline resuming with decision={req.decision!r}",
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_status(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, f"job_id {job_id!r} not found")

    app      = _get_app()
    config   = {"configurable": {"thread_id": job_id}}
    snapshot = app.get_state(config)
    state    = snapshot.values or {}

    # Detect Human Gate pause: next node is human_gate
    next_nodes   = snapshot.next or ()
    current_node = next_nodes[0] if next_nodes else "end"

    # Derive human-readable status — also check _jobs for explicit failure/cancel
    job_meta = _jobs.get(job_id, {})
    if state.get("status") in ("done", "failed"):
        derived_status = state["status"]
    elif job_meta.get("status") == "failed":
        derived_status = "failed"
    elif current_node == "human_gate":
        derived_status = "waiting_approval"
    elif current_node == "end" and not state:
        # No checkpoint yet — pipeline is still starting
        derived_status = "running"
    else:
        derived_status = "running"

    # current_node "end" means nothing is next — map to readable value
    readable_node = current_node if current_node != "end" else (
        state.get("status", "running")  # "done", "failed", or "running"
    )

    return JobStatusResponse(
        job_id=job_id,
        status=derived_status,
        current_node=readable_node,
        iteration=state.get("iteration", 0),
        qa_analyser_iteration=state.get("qa_analyser_iteration", 0),
        artifact_paths=state.get("artifact_paths", {}),
        tasks=state.get("tasks", []),
        spec=state.get("spec"),
        test_report=state.get("test_report"),
        history=state.get("history", []),
        cost_estimate_usd=_sum_cost(state.get("history", [])),
        project_dir=state.get("project_dir"),
        spec_dir=state.get("spec_dir"),
    )


def _sum_cost(history: list[dict]) -> float | None:
    """Sum token costs from history if mode=api (Mode B has no API cost)."""
    if not history:
        return None
    if any("mode=api" in e.get("note", "") for e in history):
        return None   # TODO: compute from token usage when Mode A is implemented
    return 0.0        # Mode B: $0 extra


@router.get("/stream/{job_id}")
async def stream_events(job_id: str):
    """
    Server-Sent Events — streams LangGraph node_start / node_end events
    for a running pipeline job.
    """
    if job_id not in _jobs:
        raise HTTPException(404, f"job_id {job_id!r} not found")

    async def _generate() -> AsyncGenerator[str, None]:
        app    = _get_app()
        config = {"configurable": {"thread_id": job_id}}

        # Stream events from the existing checkpoint thread (read-only — no re-invocation)
        try:
            async for event in app.astream_events(
                None,           # None = don't reinvoke; stream from existing thread state
                config,
                version="v2",
            ):
                payload = json.dumps({
                    "event": event["event"],
                    "name":  event.get("name", ""),
                    "data":  str(event.get("data", ""))[:500],  # truncate for SSE safety
                })
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0)
        except Exception as exc:
            yield f'data: {{"event":"error","message":{json.dumps(str(exc))}}}\n\n'

        yield 'data: {"event":"stream_end"}\n\n'

    return StreamingResponse(_generate(), media_type="text/event-stream")


@router.post("/cancel/{job_id}", response_model=CancelJobResponse)
async def cancel_job(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, f"job_id {job_id!r} not found")
    _jobs[job_id]["status"] = "failed"
    # Note: in-flight claude subprocess continues until it finishes naturally.
    # True cancellation requires process tracking — future work for production.
    return CancelJobResponse(job_id=job_id, message="Job marked cancelled (in-flight subprocess may still complete)")
