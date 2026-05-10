"""
LangGraph graph — nodes, edges, routing, human gate, compile.

Control plane is deterministic Python — no LLM decides next state.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt

from orchestrator.context import ProjectContext
from orchestrator.backends import get_backend

logger = logging.getLogger(__name__)

MAX_QA_ITERATIONS          = int(os.getenv("MAX_QA_ITERATIONS", "3"))
MAX_QA_ANALYSER_ITERATIONS = int(os.getenv("MAX_QA_ANALYSER_ITERATIONS", "2"))
CHECKPOINT_DB              = os.getenv("CHECKPOINT_DB", "./data/checkpoints.sqlite")


# ── Node factories ────────────────────────────────────────────────────────────

def _make_agent_node(agent_name: str):
    """Return an async LangGraph node that runs the named agent via active backend."""
    async def node(state: ProjectContext) -> ProjectContext:
        backend = get_backend()
        logger.info("[graph] → %s", agent_name)
        updated = await backend.run(agent_name, state)
        logger.info("[graph] ← %s done", agent_name)
        return updated
    node.__name__ = f"{agent_name}_node"
    return node


def human_gate(state: ProjectContext) -> ProjectContext:
    """
    Pause the graph and wait for explicit human approval.
    Resume with: app.invoke(Command(resume="approve"), config)
    Reject  with: app.invoke(Command(resume="reject"), config)
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
    return {**state, "status": "done"}  # type: ignore[return-value]


def handle_failed(state: ProjectContext) -> ProjectContext:
    logger.warning("[graph] ❌ Pipeline FAILED — job_id=%s", state.get("job_id"))
    return {**state, "status": "failed"}  # type: ignore[return-value]


# ── Graph compilation ─────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    g = StateGraph(ProjectContext)

    # Nodes
    g.add_node("pm",         _make_agent_node("pm"))
    g.add_node("analyser",   _make_agent_node("analyser"))
    g.add_node("human_gate", human_gate)
    g.add_node("engineer",   _make_agent_node("engineer"))
    g.add_node("qa",         _make_agent_node("qa"))
    g.add_node("done",       handle_done)
    g.add_node("failed",     handle_failed)

    # Edges
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


def compile_app(checkpointer=None):
    """
    Compile the LangGraph app with checkpoint and human gate interrupt.

    Usage:
        app = compile_app()
        app.invoke(initial_state, config={"configurable": {"thread_id": job_id}})
    """
    import os, pathlib
    pathlib.Path(CHECKPOINT_DB).parent.mkdir(parents=True, exist_ok=True)

    if checkpointer is None:
        checkpointer = SqliteSaver.from_conn_string(CHECKPOINT_DB)

    graph = build_graph()
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_gate"],
    )
