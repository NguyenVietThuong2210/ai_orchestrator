"""
LangGraph graph — nodes, edges, routing, human gate, compile.

Control plane is deterministic Python — no LLM decides next state.

Adaptive flow by pipeline_intent (set by PM):
  query  → PM → Analyser → done
  test   → PM → Analyser → QA → done
  review → PM → Analyser → Reviewer → done
  bug_fix→ PM → [clarification?] → Analyser → Engineer → QA → done
  feature→ PM → [clarification?] → Analyser → SpecAnalyze
                → [approved] → TaskDecompose → [human_gate]
                → Engineer → Reviewer → Security → QA
                QA pass → Deploy → Retrospective → DONE
                QA fail-minor (≤3x) → Engineer
                QA fail-major (≤2x) → Analyser → SpecAnalyze → ...
                loops exhausted → Retrospective → FAILED
                security fail   → Retrospective → FAILED
                deploy fail     → Retrospective → FAILED
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
MAX_SPEC_REVISIONS         = int(os.getenv("MAX_SPEC_REVISIONS", "2"))
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
        **Intent:** {state.get('pipeline_intent', 'feature')}

        ---

        {state.get('request', '')}
    """)
    _w(sd / "00_requirements.md", md)
    _update_manifest(sd, {
        "job_id":          state.get("job_id"),
        "started":         ts,
        "request":         state.get("request"),
        "pipeline_intent": state.get("pipeline_intent", "feature"),
        "steps":           {},
    })


def _write_pm_tasks(state: ProjectContext, sd: pathlib.Path) -> None:
    tasks = state.get("tasks", [])
    dod   = state.get("definition_of_done", [])
    intent = state.get("pipeline_intent", "feature")
    _w(sd / "01_pm_tasks.json", _json({"tasks": tasks, "definition_of_done": dod, "intent": intent}))

    rows = "\n".join(
        f"| {t.get('id','?')} | {t.get('title','')} | P{t.get('priority',3)} "
        f"| {t.get('status','pending')} | {t.get('phase','Stories')} | {t.get('description','')} |"
        for t in tasks
    )
    dod_md = "\n".join(f"- [ ] {c}" for c in dod)
    spec_md = state.get("spec_md", "")
    md = dedent(f"""\
        # PM Output

        **Intent:** `{intent}`

        ## Task Breakdown

        | ID | Title | Priority | Status | Phase | Description |
        |----|-------|----------|--------|-------|-------------|
        {rows}

        ## Definition of Done

        {dod_md or '_Not specified_'}
    """)
    if spec_md:
        md += f"\n## spec.md (speckit:specify)\n\n{spec_md}\n"

    _w(sd / "01_pm_tasks.md", md)

    constitution = state.get("constitution", "")
    if constitution:
        _w(sd / "specs" / "constitution.md", constitution)

    if spec_md:
        _w(sd / "specs" / "spec.md", spec_md)

    _update_manifest(sd, {"steps": {
        "pm": {"file": "01_pm_tasks.json", "tasks": len(tasks), "intent": intent}
    }})


def _write_technical_spec(state: ProjectContext, sd: pathlib.Path) -> None:
    spec = state.get("spec") or {}
    _w(sd / "02_technical_spec.json", _json(spec))
    components = "\n".join(
        f"- **{c.get('name','')}**: {c.get('responsibility', c.get('description',''))}"
        for c in spec.get("components", [])
    )
    apis = "\n".join(
        f"- `{c.get('method','GET')} {c.get('path','')}` → {c.get('response','')}"
        for c in spec.get("api_contracts", [])
    )
    risks = "\n".join(f"- ⚠ {r.get('description','')}" for r in spec.get("risks", []))
    criteria = "\n".join(f"- [ ] {c}" for c in spec.get("acceptance_criteria", []))
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

    plan_md = state.get("plan_md", "")
    if plan_md:
        _w(sd / "specs" / "plan.md", plan_md)

    _update_manifest(sd, {"steps": {"analyser": {"file": "02_technical_spec.json"}}})


def _write_spec_analysis(state: ProjectContext, sd: pathlib.Path) -> None:
    analysis = state.get("spec_analysis") or {}
    revision = state.get("spec_revision_count", 0)
    _w(sd / f"02b_spec_analysis_r{revision}.json", _json(analysis))
    findings = analysis.get("findings", [])
    rows = "\n".join(
        f"| {f.get('pass_name','')} | {f.get('severity','')} | {f.get('location','')} "
        f"| {f.get('description','')} | {f.get('suggestion','')} |"
        for f in findings
    )
    approved = "✅ Approved" if analysis.get("approved") else "❌ Needs Revision"
    md = dedent(f"""\
        # Spec Analysis Report (revision #{revision})

        **Result:** {approved}
        **Summary:** {analysis.get('summary', '')}

        ## Findings

        | Pass | Severity | Location | Description | Suggestion |
        |------|----------|----------|-------------|------------|
        {rows or '_No findings_'}
    """)
    _w(sd / f"02b_spec_analysis_r{revision}.md", md)
    _update_manifest(sd, {"steps": {
        f"spec_analyze_r{revision}": {"approved": analysis.get("approved"), "findings": len(findings)}
    }})


def _write_task_decompose(state: ProjectContext, sd: pathlib.Path) -> None:
    tasks = state.get("tasks", [])
    tasks_md = state.get("tasks_md", "")
    _w(sd / "02c_tasks.json", _json(tasks))
    if tasks_md:
        _w(sd / "specs" / "tasks.md", tasks_md)
        _w(sd / "02c_tasks.md", tasks_md)
    _update_manifest(sd, {"steps": {"task_decompose": {"tasks": len(tasks)}}})


def _write_engineer_summary(state: ProjectContext, sd: pathlib.Path) -> None:
    payload = {"artifact_paths": state.get("artifact_paths", {}), "iteration": state.get("iteration", 0)}
    _w(sd / "03_engineer_summary.json", _json(payload))
    files = "\n".join(f"- `{name}` → `{path}`" for name, path in state.get("artifact_paths", {}).items())
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
    _w(sd / fname.replace(".json", ".md"), md)
    _update_manifest(sd, {"steps": {f"qa{'_r'+str(iteration) if iteration else ''}":
                                    {"file": fname, "status": report.get("status")}}})


def _write_code_review(state: ProjectContext, sd: pathlib.Path) -> None:
    report = state.get("code_review_report") or {}
    _w(sd / "05_code_review.json", _json(report))
    issues = "\n".join(
        f"- [{i.get('severity','?').upper()}] `{i.get('file','')}:{i.get('line','')}` — {i.get('description','')}"
        for i in report.get("issues", [])
    )
    md = dedent(f"""\
        # Code Review Report
        **Status:** {report.get('status', '?')}
        **Summary:** {report.get('summary', '')}
        ## Issues
        {issues or '_None_'}
    """)
    _w(sd / "05_code_review.md", md)
    _update_manifest(sd, {"steps": {"reviewer": {"file": "05_code_review.json",
                                                  "status": report.get("status")}}})


def _write_security_report(state: ProjectContext, sd: pathlib.Path) -> None:
    report = state.get("security_report") or {}
    _w(sd / "06_security_report.json", _json(report))
    vulns = "\n".join(
        f"- [{v.get('severity','?').upper()}] {v.get('tool','?')} {v.get('id','')} — {v.get('description','')} (`{v.get('file','')}`)"
        for v in report.get("vulnerabilities", [])
    )
    md = dedent(f"""\
        # Security Report
        **Status:** {report.get('status', '?')}
        **Summary:** {report.get('summary', '')}
        ## Vulnerabilities
        {vulns or '_None_'}
    """)
    _w(sd / "06_security_report.md", md)
    _update_manifest(sd, {"steps": {"security": {"file": "06_security_report.json",
                                                  "status": report.get("status")}}})


def _write_deploy_report(state: ProjectContext, sd: pathlib.Path) -> None:
    report = state.get("deploy_report") or {}
    _w(sd / "07_deploy_report.json", _json(report))
    md = dedent(f"""\
        # Deploy Report
        **Status:** {report.get('status', '?')}
        **Endpoint:** {report.get('endpoint', '?')}
        **Response:** {report.get('response', '?')}
        **Command:** `{report.get('command_used', '?')}`
    """)
    _w(sd / "07_deploy_report.md", md)
    _update_manifest(sd, {"steps": {"deploy": {"file": "07_deploy_report.json",
                                                "status": report.get("status")}}})


def _write_retrospective(state: ProjectContext, sd: pathlib.Path) -> None:
    retro = state.get("retrospective") or {}
    _w(sd / "08_retrospective.json", _json(retro))
    worked  = "\n".join(f"- ✓ {x}" for x in retro.get("what_worked", []))
    failed  = "\n".join(f"- ✗ {x}" for x in retro.get("what_failed", []))
    lessons = "\n".join(f"- 💡 {x}" for x in retro.get("lessons", []))
    metrics = retro.get("metrics", {})
    md = dedent(f"""\
        # Project Retrospective
        ## What Worked
        {worked or '_None_'}
        ## What Failed
        {failed or '_None_'}
        ## Lessons Learned
        {lessons or '_None_'}
        ## Metrics
        - Total agents: {metrics.get('total_agents', '?')}
        - Total tokens: {metrics.get('total_tokens', '?')}
        - QA retries: {metrics.get('qa_retries', '?')}
        - Spec retries: {metrics.get('spec_retries', '?')}
        - Duration: {metrics.get('duration_seconds', '?')}s
    """)
    _w(sd / "08_retrospective.md", md)
    _update_manifest(sd, {"steps": {"retrospective": {"file": "08_retrospective.json"}},
                          "completed": datetime.now(timezone.utc).isoformat()})


_SPEC_WRITERS = {
    "pm":              _write_pm_tasks,
    "analyser":        _write_technical_spec,
    "spec_analyze":    _write_spec_analysis,
    "task_decompose":  _write_task_decompose,
    "engineer":        _write_engineer_summary,
    "qa":              _write_qa_report,
    "reviewer":        _write_code_review,
    "security":        _write_security_report,
    "deploy":          _write_deploy_report,
    "retrospective":   _write_retrospective,
}


def write_step_spec(agent_name: str, state: ProjectContext) -> None:
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
    async def node(state: ProjectContext) -> ProjectContext:
        backend = get_backend()
        logger.info("[graph] → %s", agent_name)

        # Check for pause request before running agent
        if state.get("pause_requested"):
            logger.info("[graph] ⏸  Pause requested before %s", agent_name)
            pause_decision = interrupt({"message": f"Pipeline paused before {agent_name}.", "job_id": state.get("job_id")})
            state = {**state, "pause_requested": False}  # type: ignore[assignment]

        updated = await backend.run(agent_name, state)
        logger.info("[graph] ← %s done", agent_name)

        project_dir = updated.get("project_dir") or _derive_project_dir(updated)
        updated = {**updated, "project_dir": project_dir,
                   "spec_dir": str(pathlib.Path(project_dir) / "spec")}
        write_step_spec(agent_name, updated)

        return updated  # type: ignore[return-value]
    node.__name__ = f"{agent_name}_node"
    return node


def clarification_gate(state: ProjectContext) -> ProjectContext:
    """
    Pause the graph and ask the user for clarification before Analyser runs.
    Resume with: Command(resume=<clarification_text>)
    """
    logger.info("[graph] ⏸  Clarification Gate — PM needs more info")
    clarification_context = interrupt({
        "message": "PM has questions before analysis can begin.",
        "questions": state.get("clarification_questions", []),
        "job_id":    state.get("job_id"),
    })
    logger.info("[graph] ▶  Clarification received — proceeding to Analyser")
    return {**state, "clarification_context": str(clarification_context)}  # type: ignore[return-value]


def human_gate(state: ProjectContext) -> ProjectContext:
    """
    Pause the graph and wait for explicit human approval of the technical spec.
    Resume with: Command(resume="approve")
    """
    logger.info("[graph] ⏸  Human Gate — waiting for spec approval")
    decision = interrupt({
        "message": "Review the spec below and approve or reject.",
        "spec":    state.get("spec"),
        "spec_md": state.get("spec_md"),
        "plan_md": state.get("plan_md"),
        "tasks_md": state.get("tasks_md"),
        "job_id":  state.get("job_id"),
    })
    if decision != "approve":
        raise ValueError(f"Spec rejected by user (decision={decision!r})")
    logger.info("[graph] ▶  Human Gate approved — proceeding to Engineering")
    return state


# ── Routing ───────────────────────────────────────────────────────────────────

def route_pm(state: ProjectContext) -> str:
    """After PM: ask for clarification or proceed to Analyser."""
    if state.get("needs_clarification"):
        logger.info("[graph] PM needs clarification → clarification_gate")
        return "clarification_gate"
    return "analyser"


def route_analyser(state: ProjectContext) -> str:
    """After Analyser: branch by pipeline intent."""
    intent = state.get("pipeline_intent", "feature")
    if intent == "query":
        logger.info("[graph] intent=query → done")
        return "done"
    if intent == "test":
        logger.info("[graph] intent=test → qa (skip engineer)")
        return "qa"
    if intent == "review":
        logger.info("[graph] intent=review → reviewer")
        return "reviewer"
    if intent == "bug_fix":
        logger.info("[graph] intent=bug_fix → engineer")
        return "engineer"
    # feature — run SpecAnalyze
    logger.info("[graph] intent=feature → spec_analyze")
    return "spec_analyze"


def route_spec_analyze(state: ProjectContext) -> str:
    """After SpecAnalyze: proceed to TaskDecompose or send back to Analyser for revision."""
    analysis = state.get("spec_analysis") or {}
    if analysis.get("approved"):
        logger.info("[graph] Spec approved → task_decompose")
        return "task_decompose"
    revision = state.get("spec_revision_count", 0)
    if revision >= MAX_SPEC_REVISIONS:
        logger.warning("[graph] Spec revision limit (%d) hit → retrospective", MAX_SPEC_REVISIONS)
        return "retrospective"
    logger.info("[graph] Spec needs revision (rev %d) → analyser", revision)
    return "analyser"


def route_reviewer(state: ProjectContext) -> str:
    """After Code Review: proceed to security, retry engineer, or terminal."""
    intent = state.get("pipeline_intent", "feature")
    report = state.get("code_review_report") or {}

    # For review-only intent: always done after reviewer
    if intent == "review":
        return "done"

    if report.get("status") == "fail":
        iteration = state.get("iteration", 0) + 1
        if iteration >= MAX_QA_ITERATIONS:
            logger.warning("[graph] Code review loop exhausted (%d) → retrospective", iteration)
            return "retrospective"
        logger.info("[graph] Code review failed → Engineer retry #%d", iteration)
        return "engineer"
    return "security"


def route_security(state: ProjectContext) -> str:
    """After Security scan: proceed to QA or stop with retrospective."""
    report = state.get("security_report") or {}
    status = report.get("status", "pass")
    if status == "fail":
        logger.warning("[graph] Security scan FAILED → retrospective")
        return "retrospective"
    if status == "warn":
        logger.info("[graph] Security scan WARN — proceeding to QA with warnings logged")
    return "qa"


def route_qa(state: ProjectContext) -> str:
    """After QA: route to deploy, retry engineer/analyser, or retrospective."""
    report = state.get("test_report")
    if report is None:
        logger.error("[graph] route_qa called but test_report is None")
        return "retrospective"

    status = report["status"]

    if status == "pass":
        intent = state.get("pipeline_intent", "feature")
        # test-only and bug_fix intents skip deploy
        if intent in ("test", "bug_fix"):
            return "done"
        return "deploy"

    if status == "fail-major":
        if state.get("qa_analyser_iteration", 0) >= MAX_QA_ANALYSER_ITERATIONS:
            logger.warning("[graph] QA→Analyser loop exhausted (%d/%d) → retrospective",
                           state["qa_analyser_iteration"], MAX_QA_ANALYSER_ITERATIONS)
            return "retrospective"
        return "analyser"

    # fail-minor
    if state.get("iteration", 0) >= MAX_QA_ITERATIONS:
        logger.warning("[graph] QA→Engineer loop exhausted (%d/%d) → retrospective",
                       state["iteration"], MAX_QA_ITERATIONS)
        return "retrospective"
    return "engineer"


def route_retrospective(state: ProjectContext) -> str:
    """After Retrospective: done if deploy passed, failed otherwise."""
    deploy = state.get("deploy_report") or {}
    if deploy.get("status") == "pass":
        return "done"
    return "failed"


# ── Terminal nodes ────────────────────────────────────────────────────────────

def _drain_message_queue(state: ProjectContext) -> ProjectContext:
    """Discard unprocessed messages at terminal nodes and append them to the
    interaction_log for auditability.  Without draining, stale messages
    accumulate in the checkpoint and replay on any future resume."""
    queue = state.get("user_message_queue", [])
    if not queue:
        return {**state, "user_message_queue": []}  # type: ignore[return-value]
    logger.info("[graph] draining %d unprocessed message(s) from queue", len(queue))
    log = list(state.get("interaction_log", []))
    log.extend([{**m, "drained_at": "terminal"} for m in queue])
    return {**state, "user_message_queue": [], "interaction_log": log}  # type: ignore[return-value]


def handle_done(state: ProjectContext) -> ProjectContext:
    logger.info("[graph] ✅ Pipeline DONE — job_id=%s intent=%s",
                state.get("job_id"), state.get("pipeline_intent"))
    state = _drain_message_queue(state)
    sd = _spec_dir(state)
    try:
        _update_manifest(sd, {"final_status": "done"})
    except Exception:
        pass
    return {**state, "status": "done"}  # type: ignore[return-value]


def handle_failed(state: ProjectContext) -> ProjectContext:
    logger.warning("[graph] ❌ Pipeline FAILED — job_id=%s", state.get("job_id"))
    state = _drain_message_queue(state)
    sd = _spec_dir(state)
    try:
        _update_manifest(sd, {"final_status": "failed"})
    except Exception:
        pass
    return {**state, "status": "failed"}  # type: ignore[return-value]


# ── Graph compilation ─────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    g = StateGraph(ProjectContext)

    # ── Nodes ─────────────────────────────────────────────────────────────────
    g.add_node("pm",                _make_agent_node("pm"))
    g.add_node("clarification_gate", clarification_gate)
    g.add_node("analyser",          _make_agent_node("analyser"))
    g.add_node("spec_analyze",      _make_agent_node("spec_analyze"))
    g.add_node("task_decompose",    _make_agent_node("task_decompose"))
    g.add_node("human_gate",        human_gate)
    g.add_node("engineer",          _make_agent_node("engineer"))
    g.add_node("reviewer",          _make_agent_node("reviewer"))
    g.add_node("security",          _make_agent_node("security"))
    g.add_node("qa",                _make_agent_node("qa"))
    g.add_node("deploy",            _make_agent_node("deploy"))
    g.add_node("retrospective",     _make_agent_node("retrospective"))
    g.add_node("done",              handle_done)
    g.add_node("failed",            handle_failed)

    # ── Edges ──────────────────────────────────────────────────────────────────
    g.set_entry_point("pm")

    # PM → clarification or analyser
    g.add_conditional_edges("pm", route_pm, {
        "clarification_gate": "clarification_gate",
        "analyser":           "analyser",
    })
    g.add_edge("clarification_gate", "analyser")

    # Analyser → intent-based branching
    g.add_conditional_edges("analyser", route_analyser, {
        "done":         "done",        # query intent
        "qa":           "qa",          # test intent
        "reviewer":     "reviewer",    # review intent
        "engineer":     "engineer",    # bug_fix intent
        "spec_analyze": "spec_analyze", # feature intent
    })

    # SpecAnalyze → approved or revise
    g.add_conditional_edges("spec_analyze", route_spec_analyze, {
        "task_decompose": "task_decompose",
        "analyser":       "analyser",      # revision loop
        "retrospective":  "retrospective", # exhausted
    })

    # TaskDecompose → Human Gate (spec approval before engineering)
    g.add_edge("task_decompose", "human_gate")
    g.add_edge("human_gate",     "engineer")

    # Engineering → Review → Security → QA
    g.add_edge("engineer", "reviewer")
    g.add_conditional_edges("reviewer", route_reviewer, {
        "security":      "security",
        "engineer":      "engineer",
        "retrospective": "retrospective",
        "done":          "done",      # review-only intent
    })
    g.add_conditional_edges("security", route_security, {
        "qa":            "qa",
        "retrospective": "retrospective",
    })
    g.add_conditional_edges("qa", route_qa, {
        "deploy":        "deploy",
        "done":          "done",       # test/bug_fix intent skip deploy
        "engineer":      "engineer",
        "analyser":      "analyser",
        "retrospective": "retrospective",
    })

    # Deploy → Retrospective → terminal
    g.add_edge("deploy", "retrospective")
    g.add_conditional_edges("retrospective", route_retrospective, {
        "done":   "done",
        "failed": "failed",
    })
    g.add_edge("done",   END)
    g.add_edge("failed", END)

    return g


# ── Async singleton ───────────────────────────────────────────────────────────

_app = None
_checkpointer: AsyncPostgresSaver | None = None
_checkpointer_cm = None


async def get_app():
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
    global _app, _checkpointer, _checkpointer_cm
    if _checkpointer_cm is not None:
        try:
            await _checkpointer_cm.__aexit__(None, None, None)
        except Exception:
            logger.exception("Error closing checkpointer")
    _app = None
    _checkpointer = None
    _checkpointer_cm = None
