"""
LangGraph graph — nodes, edges, routing, human gate, compile.

Control plane is deterministic Python — no LLM decides next state.
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import re
from datetime import datetime, timezone
from textwrap import dedent

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import interrupt

from orchestrator.context import ProjectContext
from orchestrator.backends import get_backend

logger = logging.getLogger(__name__)

MAX_QA_ITERATIONS          = int(os.getenv("MAX_QA_ITERATIONS", "3"))
MAX_QA_ANALYSER_ITERATIONS = int(os.getenv("MAX_QA_ANALYSER_ITERATIONS", "2"))
PROJECTS_ROOT              = os.getenv("PROJECTS_ROOT", "./projects")


def _require_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Set it to a PostgreSQL connection string, e.g.: "
            "postgresql://user:pass@localhost:5432/orchestrator"
        )
    return url


# ── Spec-file helpers ─────────────────────────────────────────────────────────

def _derive_project_dir(state: ProjectContext) -> str:
    """
    Extract the project directory from the requirement text.
    Looks for patterns like:  projects/hello_django/  or  project/hello_django
    Falls back to  projects/<job_id[:8]>/
    """
    request = state.get("request", "")
    m = re.search(r"projects?/([A-Za-z0-9_\-]+)", request, re.IGNORECASE)
    if m:
        return f"{PROJECTS_ROOT}/{m.group(1)}"
    return f"{PROJECTS_ROOT}/{state.get('job_id', 'unknown')[:8]}"


def _spec_dir(state: ProjectContext) -> pathlib.Path:
    project_dir = state.get("project_dir") or _derive_project_dir(state)
    return pathlib.Path(project_dir) / "spec"


def _manifest_path(sd: pathlib.Path) -> pathlib.Path:
    return sd / "_pipeline.json"


def _update_manifest(sd: pathlib.Path, update: dict) -> None:
    """Merge update into _pipeline.json manifest."""
    manifest: dict = {}
    mp = _manifest_path(sd)
    if mp.exists():
        try:
            manifest = json.loads(mp.read_text(encoding="utf-8"))
        except Exception:
            pass
    manifest.update(update)
    mp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def _w(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info("[spec] wrote %s", path)


def _json(obj: object) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


# ── Per-step spec writers ─────────────────────────────────────────────────────

def _write_requirements(state: ProjectContext, sd: pathlib.Path) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    md = dedent(f"""\
        # Requirements

        **Job:** `{state.get('job_id')}`
        **Started:** {ts}

        ---

        {state.get('request', '')}
    """)
    _w(sd / "00_requirements.md", md)
    _update_manifest(sd, {
        "job_id":  state.get("job_id"),
        "started": ts,
        "request": state.get("request"),
        "steps":   {},
    })


def _write_pm_tasks(state: ProjectContext, sd: pathlib.Path) -> None:
    tasks = state.get("tasks", [])
    _w(sd / "01_pm_tasks.json", _json(tasks))

    rows = "\n".join(
        f"| {t.get('id','?')} | {t.get('title','')} | P{t.get('priority',3)} "
        f"| {t.get('status','pending')} | {t.get('description','')} |"
        for t in tasks
    )
    md = dedent(f"""\
        # PM Task Breakdown

        | ID | Title | Priority | Status | Description |
        |----|-------|----------|--------|-------------|
        {rows}
    """)
    _w(sd / "01_pm_tasks.md", md)
    _update_manifest(sd, {"steps": {"pm": {"file": "01_pm_tasks.json", "tasks": len(tasks)}}})


def _write_technical_spec(state: ProjectContext, sd: pathlib.Path) -> None:
    spec = state.get("spec") or {}
    _w(sd / "02_technical_spec.json", _json(spec))

    components = "\n".join(
        f"- **{c.get('name','')}**: {c.get('description','')}"
        for c in spec.get("components", [])
    )
    apis = "\n".join(
        f"- `{c.get('method','GET')} {c.get('path','')}` → {c.get('response','')}"
        for c in spec.get("api_contracts", [])
    )
    risks = "\n".join(
        f"- ⚠ {r.get('description','')}"
        for r in spec.get("risks", [])
    )
    criteria = "\n".join(
        f"- [ ] {c}" for c in spec.get("acceptance_criteria", [])
    )
    md = dedent(f"""\
        # Technical Spec

        ## Overview

        {spec.get('overview', '_Not provided_')}

        ## Components

        {components or '_None_'}

        ## API Contracts

        {apis or '_None_'}

        ## Risks

        {risks or '_None_'}

        ## Acceptance Criteria

        {criteria or '_None_'}
    """)
    _w(sd / "02_technical_spec.md", md)
    _update_manifest(sd, {"steps": {"analyser": {"file": "02_technical_spec.json"}}})


def _write_engineer_summary(state: ProjectContext, sd: pathlib.Path) -> None:
    payload = {
        "artifact_paths": state.get("artifact_paths", {}),
        "iteration":      state.get("iteration", 0),
    }
    _w(sd / "03_engineer_summary.json", _json(payload))

    files = "\n".join(
        f"- `{name}` → `{path}`"
        for name, path in state.get("artifact_paths", {}).items()
    )
    md = dedent(f"""\
        # Engineer Implementation Summary

        **Iteration:** {state.get('iteration', 0)}

        ## Generated Files

        {files or '_None yet_'}
    """)
    _w(sd / "03_engineer_summary.md", md)
    _update_manifest(sd, {"steps": {"engineer": {"file": "03_engineer_summary.json",
                                                  "files": len(state.get("artifact_paths", {}))}}})


def _write_qa_report(state: ProjectContext, sd: pathlib.Path) -> None:
    report = state.get("test_report") or {}
    iteration = state.get("iteration", 0)
    suffix = f"_r{iteration}" if iteration > 0 else ""
    fname  = f"04_qa_report{suffix}.json"
    _w(sd / fname, _json(report))

    defects = "\n".join(
        f"- [{d.get('severity','?').upper()}] `{d.get('file','')}:{d.get('line','')}` — {d.get('description','')}"
        for d in report.get("defects", [])
    )
    passed = "\n".join(f"- ✓ {t}" for t in report.get("passed", []))
    failed = "\n".join(f"- ✗ {t}" for t in report.get("failed", []))
    md = dedent(f"""\
        # QA Report{f' (retry {iteration})' if iteration else ''}

        **Status:** {report.get('status', '?')}
        **Summary:** {report.get('summary', '')}

        ## Passed Tests

        {passed or '_None_'}

        ## Failed Tests

        {failed or '_None_'}

        ## Defects

        {defects or '_None_'}
    """)
    mdfname = fname.replace(".json", ".md")
    _w(sd / mdfname, md)
    _update_manifest(sd, {"steps": {f"qa{'_r'+str(iteration) if iteration else ''}":
                                    {"file": fname, "status": report.get("status")}}})


_SPEC_WRITERS = {
    "pm":       _write_pm_tasks,
    "analyser": _write_technical_spec,
    "engineer": _write_engineer_summary,
    "qa":       _write_qa_report,
}


def write_step_spec(agent_name: str, state: ProjectContext) -> None:
    """Called after each agent node completes — writes spec files to disk."""
    writer = _SPEC_WRITERS.get(agent_name)
    if not writer:
        return
    try:
        sd = _spec_dir(state)
        sd.mkdir(parents=True, exist_ok=True)
        writer(state, sd)
    except Exception:
        logger.exception("[spec] failed to write spec for agent=%s", agent_name)


# ── Node factories ────────────────────────────────────────────────────────────

def _make_agent_node(agent_name: str):
    """Return an async LangGraph node that runs the named agent via active backend."""
    async def node(state: ProjectContext) -> ProjectContext:
        backend = get_backend()
        logger.info("[graph] → %s", agent_name)
        updated = await backend.run(agent_name, state)
        logger.info("[graph] ← %s done", agent_name)

        project_dir = updated.get("project_dir") or _derive_project_dir(updated)
        updated = {**updated, "project_dir": project_dir,
                   "spec_dir": str(pathlib.Path(project_dir) / "spec")}
        write_step_spec(agent_name, updated)

        return updated  # type: ignore[return-value]
    node.__name__ = f"{agent_name}_node"
    return node


def human_gate(state: ProjectContext) -> ProjectContext:
    """
    Pause the graph and wait for explicit human approval.
    Resume with: app.invoke(Command(resume="approve"), config)
    """
    logger.info("[graph] ⏸  Human Gate — waiting for spec approval")
    decision = interrupt({
        "message": "Review the spec below and approve or reject.",
        "spec":    state.get("spec"),
        "job_id":  state.get("job_id"),
    })
    if decision != "approve":
        raise ValueError(f"Spec rejected by user (decision={decision!r})")
    logger.info("[graph] ▶  Human Gate approved — proceeding to Engineering")
    return state


# ── Routing ───────────────────────────────────────────────────────────────────

def route_qa(state: ProjectContext) -> str:
    report = state.get("test_report")
    if report is None:
        logger.error("[graph] route_qa called but test_report is None")
        return "failed"

    status = report["status"]

    if status == "pass":
        return "done"

    if status == "fail-major":
        if state.get("qa_analyser_iteration", 0) >= MAX_QA_ANALYSER_ITERATIONS:
            logger.warning("[graph] QA→Analyser loop exhausted (%d/%d) → FAILED",
                           state["qa_analyser_iteration"], MAX_QA_ANALYSER_ITERATIONS)
            return "failed"
        return "analyser"

    # fail-minor
    if state.get("iteration", 0) >= MAX_QA_ITERATIONS:
        logger.warning("[graph] QA→Engineer loop exhausted (%d/%d) → FAILED",
                       state["iteration"], MAX_QA_ITERATIONS)
        return "failed"
    return "engineer"


# ── Terminal nodes ────────────────────────────────────────────────────────────

def handle_done(state: ProjectContext) -> ProjectContext:
    logger.info("[graph] ✅ Pipeline DONE — job_id=%s", state.get("job_id"))
    sd = _spec_dir(state)
    _update_manifest(sd, {"completed": datetime.now(timezone.utc).isoformat(), "final_status": "done"})
    return {**state, "status": "done"}  # type: ignore[return-value]


def handle_failed(state: ProjectContext) -> ProjectContext:
    logger.warning("[graph] ❌ Pipeline FAILED — job_id=%s", state.get("job_id"))
    sd = _spec_dir(state)
    _update_manifest(sd, {"completed": datetime.now(timezone.utc).isoformat(), "final_status": "failed"})
    return {**state, "status": "failed"}  # type: ignore[return-value]


# ── Graph compilation ─────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    g = StateGraph(ProjectContext)

    g.add_node("pm",         _make_agent_node("pm"))
    g.add_node("analyser",   _make_agent_node("analyser"))
    g.add_node("human_gate", human_gate)
    g.add_node("engineer",   _make_agent_node("engineer"))
    g.add_node("qa",         _make_agent_node("qa"))
    g.add_node("done",       handle_done)
    g.add_node("failed",     handle_failed)

    g.set_entry_point("pm")
    g.add_edge("pm",         "analyser")
    g.add_edge("analyser",   "human_gate")
    g.add_edge("human_gate", "engineer")
    g.add_edge("engineer",   "qa")
    g.add_conditional_edges("qa", route_qa, {
        "done":     "done",
        "failed":   "failed",
        "engineer": "engineer",
        "analyser": "analyser",
    })
    g.add_edge("done",   END)
    g.add_edge("failed", END)

    return g


# ── Async singleton ───────────────────────────────────────────────────────────

_app = None
_checkpointer: AsyncPostgresSaver | None = None
_checkpointer_cm = None


async def get_app():
    """
    Return the compiled LangGraph app (async singleton).
    Requires DATABASE_URL to be set — raises RuntimeError otherwise.
    """
    global _app, _checkpointer, _checkpointer_cm
    if _app is not None:
        return _app

    pathlib.Path(PROJECTS_ROOT).mkdir(parents=True, exist_ok=True)

    db_url = _require_database_url()
    _checkpointer_cm = AsyncPostgresSaver.from_conn_string(db_url)
    _checkpointer = await _checkpointer_cm.__aenter__()
    await _checkpointer.setup()
    logger.info("Checkpointer: AsyncPostgresSaver @ %s", db_url.split("@")[-1])

    _app = build_graph().compile(
        checkpointer=_checkpointer,
        interrupt_before=["human_gate"],
    )
    return _app


async def close_app() -> None:
    """Graceful shutdown — close PostgreSQL connection pool."""
    global _app, _checkpointer, _checkpointer_cm
    if _checkpointer_cm is not None:
        try:
            await _checkpointer_cm.__aexit__(None, None, None)
        except Exception:
            logger.exception("Error closing checkpointer")
    _app = None
    _checkpointer = None
    _checkpointer_cm = None
