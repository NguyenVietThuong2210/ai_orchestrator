"""
Test LangGraph routing logic with a mock backend.
Does NOT spawn claude subprocess or call Anthropic API.
"""
from __future__ import annotations

import pytest

from orchestrator.context import ProjectContext
from orchestrator.graph import route_qa, handle_done, handle_failed


def _base_state(**kwargs) -> ProjectContext:
    return {
        "request":               "Build a todo REST API",
        "job_id":                "test-001",
        "tasks":                 [],
        "spec":                  None,
        "artifact_paths":        {},
        "test_report":           None,
        "history":               [],
        "iteration":             0,
        "qa_analyser_iteration": 0,
        "status":                "running",
        **kwargs,
    }


# ── route_qa ──────────────────────────────────────────────────────────────────

def test_route_qa_pass():
    state = _base_state(test_report={"status": "pass", "summary": "", "passed": [], "failed": [], "defects": []})
    assert route_qa(state) == "done"


def test_route_qa_fail_minor_under_limit():
    state = _base_state(
        iteration=1,
        test_report={"status": "fail-minor", "summary": "", "passed": [], "failed": ["t1"], "defects": []},
    )
    assert route_qa(state) == "engineer"


def test_route_qa_fail_minor_at_limit():
    state = _base_state(
        iteration=3,   # == MAX_QA_ITERATIONS
        test_report={"status": "fail-minor", "summary": "", "passed": [], "failed": ["t1"], "defects": []},
    )
    assert route_qa(state) == "failed"


def test_route_qa_fail_major_under_limit():
    state = _base_state(
        qa_analyser_iteration=1,
        test_report={"status": "fail-major", "summary": "", "passed": [], "failed": [], "defects": []},
    )
    assert route_qa(state) == "analyser"


def test_route_qa_fail_major_at_limit():
    state = _base_state(
        qa_analyser_iteration=2,   # == MAX_QA_ANALYSER_ITERATIONS
        test_report={"status": "fail-major", "summary": "", "passed": [], "failed": [], "defects": []},
    )
    assert route_qa(state) == "failed"


def test_route_qa_none_report():
    state = _base_state(test_report=None)
    assert route_qa(state) == "failed"


# ── Terminal nodes ────────────────────────────────────────────────────────────

def test_handle_done_sets_status():
    state = _base_state()
    result = handle_done(state)
    assert result["status"] == "done"


def test_handle_failed_sets_status():
    state = _base_state()
    result = handle_failed(state)
    assert result["status"] == "failed"


# ── Agent parse_submit ────────────────────────────────────────────────────────

def test_pm_parse_submit():
    from agents.pm import PMAgent
    agent = PMAgent()
    state = _base_state()
    tasks = [{"id": "T1", "title": "Create schema", "description": "...", "priority": 1, "status": "pending"}]
    result = agent.parse_submit(state, {"tasks": tasks})
    assert result["tasks"] == tasks


def test_qa_parse_submit_increments_iteration():
    from agents.qa import QAAgent
    agent = QAAgent()
    state = _base_state(iteration=1)
    result = agent.parse_submit(state, {
        "status": "fail-minor", "summary": "", "passed": [], "failed": [], "defects": []
    })
    assert result["iteration"] == 2
    assert result["qa_analyser_iteration"] == 0


def test_qa_parse_submit_increments_analyser_iteration():
    from agents.qa import QAAgent
    agent = QAAgent()
    state = _base_state(qa_analyser_iteration=0)
    result = agent.parse_submit(state, {
        "status": "fail-major", "summary": "", "passed": [], "failed": [], "defects": []
    })
    assert result["qa_analyser_iteration"] == 1
    assert result["iteration"] == 0
