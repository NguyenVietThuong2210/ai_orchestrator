"""
FastAPI routes:
  POST /run-pipeline      — start pipeline
  POST /approve-spec      — resume after Human Gate
  GET  /status/{job_id}   — poll job state
  GET  /stream/{job_id}   — SSE live event stream
  POST /cancel/{job_id}   — cancel job (cancels asyncio task + kills subprocess)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from uuid import uuid4

from api.schemas import (
    RunPipelineRequest, RunPipelineResponse,
    ApproveSpecRequest, ApproveSpecResponse,
    JobStatusResponse, CancelJobResponse,
    ResumeJobResponse, JobSummary, JobListResponse,
)
from orchestrator.runner import run_pipeline, resume_pipeline
from orchestrator.graph import get_app

router = APIRouter()
logger = logging.getLogger(__name__)

# Job registry: job_id → {status, task, error}
# task is the asyncio.Task — holds a reference so we can cancel it.
_jobs: dict[str, dict] = {}


@router.post("/run-pipeline", response_model=RunPipelineResponse)
async def start_pipeline(req: RunPipelineRequest):
    job_id = req.job_id or str(uuid4())

    async def _run() -> None:
        try:
            final = await run_pipeline(req.requirement, job_id=job_id)
            _jobs[job_id]["status"] = final.get("status", "done")
        except asyncio.CancelledError:
            logger.info("Pipeline cancelled — job_id=%s", job_id)
            _jobs[job_id]["status"] = "failed"
        except Exception as exc:
            logger.exception("Pipeline error — job_id=%s", job_id)
            _jobs[job_id].update({"status": "failed", "error": str(exc)})

    task = asyncio.create_task(_run(), name=f"pipeline-{job_id}")
    _jobs[job_id] = {"status": "running", "task": task, "error": None}

    return RunPipelineResponse(
        job_id=job_id,
        status="started",
        message=f"Pipeline started. Poll GET /status/{job_id} or stream GET /stream/{job_id}",
    )


@router.post("/approve-spec", response_model=ApproveSpecResponse)
async def approve_spec(req: ApproveSpecRequest):
    # Lazily register so cancel/idempotency logic works for cross-session jobs
    if req.job_id not in _jobs:
        _jobs[req.job_id] = {"status": "unknown", "task": None, "error": None}

    # Idempotency: don't spawn a second resume task if one is already in flight
    existing = _jobs[req.job_id].get("task")
    if existing and not existing.done():
        return ApproveSpecResponse(
            job_id=req.job_id,
            status="resuming",
            message="Pipeline is already resuming — duplicate request ignored",
        )

    async def _resume() -> None:
        try:
            final = await resume_pipeline(req.job_id, decision=req.decision)
            _jobs[req.job_id]["status"] = final.get("status", "done")
        except asyncio.CancelledError:
            _jobs[req.job_id]["status"] = "failed"
        except Exception as exc:
            logger.exception("Resume error — job_id=%s", req.job_id)
            _jobs[req.job_id].update({"status": "failed", "error": str(exc)})

    task = asyncio.create_task(_resume(), name=f"resume-{req.job_id}")
    _jobs[req.job_id]["task"] = task

    return ApproveSpecResponse(
        job_id=req.job_id,
        status="resuming",
        message=f"Pipeline resuming with decision={req.decision!r}",
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_status(job_id: str):
    app      = await get_app()
    config   = {"configurable": {"thread_id": job_id}}
    snapshot = await app.aget_state(config)
    state    = snapshot.values or {}

    # 404 only when neither _jobs nor LangGraph know about this id
    if not state and job_id not in _jobs:
        raise HTTPException(404, f"job_id {job_id!r} not found")

    # Lazily register jobs that existed before this server session (e.g. MCP-started)
    if job_id not in _jobs:
        _jobs[job_id] = {"status": "unknown", "task": None, "error": None}

    next_nodes   = snapshot.next or ()
    current_node = next_nodes[0] if next_nodes else "end"

    job_meta = _jobs.get(job_id, {})
    if state.get("status") in ("done", "failed"):
        derived_status = state["status"]
    elif job_meta.get("status") == "failed":
        derived_status = "failed"
    elif current_node == "human_gate":
        derived_status = "waiting_approval"
    elif current_node == "end" and not state:
        derived_status = "running"
    else:
        derived_status = "running"

    readable_node = current_node if current_node != "end" else (
        state.get("status", "running")
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
        error=job_meta.get("error"),
    )


def _sum_cost(history: list[dict]) -> float | None:
    if not history:
        return None
    return 0.0  # Mode B: $0 API cost


@router.get("/stream/{job_id}")
async def stream_events(job_id: str):
    """SSE — streams LangGraph node events for a running pipeline job."""
    # No _jobs guard — LangGraph state is the source of truth for existing jobs

    async def _generate() -> AsyncGenerator[str, None]:
        app    = await get_app()
        config = {"configurable": {"thread_id": job_id}}
        try:
            async for event in app.astream_events(None, config, version="v2"):
                payload = json.dumps({
                    "event": event["event"],
                    "name":  event.get("name", ""),
                    "data":  str(event.get("data", ""))[:500],
                })
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0)
        except Exception as exc:
            yield f'data: {{"event":"error","message":{json.dumps(str(exc))}}}\n\n'

        yield 'data: {"event":"stream_end"}\n\n'

    return StreamingResponse(_generate(), media_type="text/event-stream")


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs():
    """
    Return recent jobs (most recent first) — used by UI to auto-detect MCP-started pipelines.
    Sources: in-memory _jobs (current session) + Postgres checkpoints (survives restarts).
    """
    # Initialize app first — this sets _checkpointer on the graph module
    app = await get_app()

    # Query Postgres checkpoints table for recent thread IDs.
    # Import the module (not the value) so we always get the current _checkpointer reference.
    import orchestrator.graph as _graph
    db_thread_ids: list[str] = []
    if _graph._checkpointer is not None:
        try:
            async with _graph._checkpointer.conn.cursor() as cur:
                await cur.execute(
                    "SELECT thread_id FROM ("
                    "  SELECT DISTINCT ON (thread_id) thread_id, checkpoint_id"
                    "  FROM checkpoints"
                    "  ORDER BY thread_id, checkpoint_id DESC"
                    ") t ORDER BY checkpoint_id DESC LIMIT 20"
                )
                rows = await cur.fetchall()
                db_thread_ids = [r["thread_id"] for r in rows]
        except Exception:
            logger.exception("Failed to query checkpoints table")

    # Merge: in-memory (newest first) then DB (removes duplicates, preserves order)
    seen: set[str] = set()
    ordered: list[str] = []
    for jid in list(reversed(list(_jobs.keys()))) + db_thread_ids:
        if jid not in seen:
            seen.add(jid)
            ordered.append(jid)

    result: list[JobSummary] = []
    for jid in ordered[:20]:
        try:
            config   = {"configurable": {"thread_id": jid}}
            snapshot = await app.aget_state(config)
            state    = snapshot.values or {}
            next_nodes = snapshot.next or ()
            current_node = next_nodes[0] if next_nodes else "end"

            # Skip jobs with no LangGraph state — deleted from DB or never checkpointed
            if not state:
                continue

            # LangGraph state is the source of truth.
            if state.get("status") in ("done", "failed"):
                derived = state["status"]
            elif current_node == "human_gate":
                derived = "waiting_approval"
            elif next_nodes:
                # Pending LangGraph work — show as running even if asyncio task died
                derived = "running"
            else:
                derived = "done"

            # Lazily register so /status/{job_id} doesn't 404
            if jid not in _jobs:
                _jobs[jid] = {"status": derived, "task": None, "error": None}

            result.append(JobSummary(job_id=jid, status=derived))
        except Exception:
            result.append(JobSummary(job_id=jid, status=_jobs.get(jid, {}).get("status", "unknown")))

    return JobListResponse(jobs=result)


@router.post("/resume/{job_id}", response_model=ResumeJobResponse)
async def resume_job(job_id: str):
    """
    Resume a failed/stalled pipeline from the last LangGraph checkpoint.
    Works when the graph has a pending next-node (e.g. analyser, engineer, qa)
    but the asyncio task died before it could run.
    Does NOT work if the LangGraph terminal nodes (done/failed) already ran.
    """
    app = await get_app()
    config = {"configurable": {"thread_id": job_id}}
    snapshot = await app.aget_state(config)

    if not snapshot.values:
        raise HTTPException(404, f"job_id {job_id!r} not found in LangGraph")

    next_nodes = snapshot.next or ()
    if not next_nodes:
        raise HTTPException(400, "Pipeline already at terminal state — cannot resume. Start a new pipeline.")

    if "human_gate" in next_nodes:
        raise HTTPException(400, "Pipeline is waiting for spec approval — use POST /approve-spec instead.")

    # Lazily register so cancel/status work
    if job_id not in _jobs:
        _jobs[job_id] = {"status": "running", "task": None, "error": None}

    # Guard: don't double-spawn
    existing = _jobs[job_id].get("task")
    if existing and not existing.done():
        return ResumeJobResponse(
            job_id=job_id,
            status="running",
            message="Pipeline is already running — duplicate request ignored",
        )

    async def _rerun() -> None:
        try:
            from orchestrator.runner import resume_pipeline
            final = await resume_pipeline(job_id, decision="approve")
            _jobs[job_id]["status"] = final.get("status", "done")
        except asyncio.CancelledError:
            _jobs[job_id]["status"] = "failed"
        except Exception as exc:
            logger.exception("Rerun error — job_id=%s", job_id)
            _jobs[job_id].update({"status": "failed", "error": str(exc)})

    task = asyncio.create_task(_rerun(), name=f"rerun-{job_id}")
    _jobs[job_id] = {"status": "running", "task": task, "error": None}

    node = next_nodes[0] if next_nodes else "unknown"
    return ResumeJobResponse(
        job_id=job_id,
        status="running",
        message=f"Pipeline resuming from checkpoint — next node: {node}",
    )


@router.post("/cancel/{job_id}", response_model=CancelJobResponse)
async def cancel_job(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, f"job_id {job_id!r} not found")

    job  = _jobs[job_id]
    task: asyncio.Task | None = job.get("task")
    if task and not task.done():
        task.cancel()
        # Give the task a moment to handle CancelledError and kill its subprocess
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

    _jobs[job_id]["status"] = "failed"
    return CancelJobResponse(job_id=job_id, message="Job cancelled")
