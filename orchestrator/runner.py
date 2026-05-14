"""
Main async runner — invoke / resume graph, stream events.

CLI usage:
    python -m orchestrator.runner "Build a REST API for a todo app"
"""
from __future__ import annotations

# load_dotenv() MUST run before any orchestrator imports so that module-level
# os.getenv() calls in graph.py (MAX_QA_ITERATIONS, CHECKPOINT_DB, etc.) pick
# up values from .env rather than just the defaults.
from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import logging
import sys
from uuid import uuid4

from langgraph.types import Command

from orchestrator.context import ProjectContext
from orchestrator.graph import get_app
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _initial_state(requirement: str, job_id: str) -> ProjectContext:
    from orchestrator.graph import _derive_project_dir, _spec_dir, _write_requirements
    import pathlib
    # Build a minimal stub state so _derive_project_dir can read the request
    stub: ProjectContext = {  # type: ignore[typeddict-item]
        "request": requirement, "job_id": job_id,
        "tasks": [], "spec": None, "artifact_paths": {},
        "test_report": None, "history": [],
        "iteration": 0, "qa_analyser_iteration": 0, "status": "running",
        "project_dir": None, "spec_dir": None,
    }
    project_dir = _derive_project_dir(stub)
    spec_d      = _spec_dir(stub)
    spec_d.mkdir(parents=True, exist_ok=True)
    # Write 00_requirements.md immediately so it's visible before any agent runs
    _write_requirements({**stub, "project_dir": project_dir, "spec_dir": str(spec_d)}, spec_d)  # type: ignore[arg-type]

    return {
        "request":               requirement,
        "job_id":                job_id,
        "tasks":                 [],
        "spec":                  None,
        "artifact_paths":        {},
        "test_report":           None,
        "history":               [],
        "iteration":             0,
        "qa_analyser_iteration": 0,
        "status":                "running",
        "project_dir":           project_dir,
        "spec_dir":              str(spec_d),
    }


async def run_pipeline(requirement: str, job_id: str | None = None) -> ProjectContext:
    """
    Start a new pipeline run.

    Returns the final ProjectContext (status == "done" or "failed").
    Pauses at Human Gate — call resume_pipeline() to continue.
    """
    job_id  = job_id or str(uuid4())
    config  = {"configurable": {"thread_id": job_id}}
    app     = await get_app()
    state   = _initial_state(requirement, job_id)

    logger.info("▶ Pipeline started — job_id=%s", job_id)

    try:
        async for event in app.astream(state, config, stream_mode="values"):
            _log_event(event)
    except Exception as exc:
        logger.error("▶ astream raised: %s: %s", type(exc).__name__, exc, exc_info=True)
        raise

    snapshot = await app.aget_state(config)
    final    = snapshot.values

    if snapshot.next == ("human_gate",):
        logger.info("⏸  Human Gate reached — awaiting approval for job_id=%s", job_id)
        logger.info("   Spec preview: %s",
                    json.dumps(final.get("spec", {}).get("overview", ""), ensure_ascii=False)[:200])

    return final


async def resume_pipeline(job_id: str, decision: str = "approve") -> ProjectContext:
    """
    Resume a paused or stalled pipeline.

    Two cases:
    1. Graph is interrupted at human_gate (snapshot.next == ("human_gate",)):
       → send Command(resume=decision) to pass the interrupt.
    2. Graph has a pending non-interrupt node (e.g. next == ("engineer",)) but
       the asyncio task died mid-flight:
       → call astream(None, config) to continue from the last checkpoint.

    decision: "approve" → continue to Engineering
              anything else → spec rejected, pipeline raises ValueError
    """
    config = {"configurable": {"thread_id": job_id}}
    app    = await get_app()

    snapshot = await app.aget_state(config)
    next_nodes = snapshot.next or ()

    # Determine correct resume strategy
    if "human_gate" in next_nodes:
        # Still at the interrupt — send the user's decision
        logger.info("▶ Resuming at human_gate — job_id=%s decision=%s", job_id, decision)
        if decision != "approve":
            raise ValueError(f"Spec rejected by user (decision={decision!r})")
        stream_input = Command(resume=decision)
    elif next_nodes:
        # Already past human_gate but stalled (task died before node ran)
        logger.info("▶ Continuing stalled pipeline from checkpoint — job_id=%s next=%s", job_id, next_nodes)
        stream_input = None
    else:
        logger.info("▶ Pipeline already complete — job_id=%s", job_id)
        return snapshot.values

    try:
        async for event in app.astream(stream_input, config, stream_mode="values"):
            _log_event(event)
    except Exception as exc:
        logger.error("▶ resume astream raised: %s: %s", type(exc).__name__, exc, exc_info=True)
        raise

    return (await app.aget_state(config)).values


def _log_event(event: dict) -> None:
    status = event.get("status", "running")
    stage  = "unknown"
    if event.get("tasks") and not event.get("spec"):
        stage = "PM done"
    elif event.get("spec") and not event.get("artifact_paths"):
        stage = "Analyser done"
    elif event.get("artifact_paths") and not event.get("test_report"):
        stage = "Engineer done"
    elif event.get("test_report"):
        stage = f"QA done ({event['test_report'].get('status', '?')})"
    logger.info("  state: %s | %s", stage, status)


# ── CLI entry point ───────────────────────────────────────────────────────────

async def _cli_main(requirement: str) -> None:
    final = await run_pipeline(requirement)

    if final.get("status") == "done":
        print("\n✅ Pipeline DONE")
        print("Artifacts:", json.dumps(final.get("artifact_paths", {}), indent=2))
    elif final.get("status") == "running":
        # Paused at Human Gate
        job_id = final.get("job_id")
        print(f"\n⏸  Human Gate — job_id: {job_id}")
        print("Spec overview:", final.get("spec", {}).get("overview", ""))
        answer = input("\nApprove spec? [approve/reject]: ").strip().lower()
        final  = await resume_pipeline(job_id, decision=answer)
        if final.get("status") == "done":
            print("\n✅ Pipeline DONE")
            print("Artifacts:", json.dumps(final.get("artifact_paths", {}), indent=2))
        else:
            print(f"\n❌ Pipeline {final.get('status', 'unknown').upper()}")
    else:
        print(f"\n❌ Pipeline {final.get('status', 'unknown').upper()}")


def main() -> None:
    """Sync entry point for pyproject.toml [project.scripts]."""
    if len(sys.argv) < 2:
        print("Usage: orchestrator \"<requirement>\"")
        sys.exit(1)
    asyncio.run(_cli_main(" ".join(sys.argv[1:])))


if __name__ == "__main__":
    main()
