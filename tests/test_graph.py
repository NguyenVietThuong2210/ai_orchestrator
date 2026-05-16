"""
Test LangGraph routing logic with a mock backend.
Does NOT spawn claude subprocess or call Anthropic API.
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, patch

from orchestrator.context import ProjectContext
from orchestrator.graph import (
    route_pm, route_reviewer, route_security, route_qa,
    route_retrospective, route_analyser, route_spec_analyze,
    handle_done, handle_failed,
)


def _base_state(**kwargs) -> ProjectContext:
    return {
        "request":                 "Build a todo REST API",
        "job_id":                  "test-001",
        "tasks":                   [],
        "spec":                    None,
        "artifact_paths":          {},
        "test_report":             None,
        "history":                 [],
        "iteration":               0,
        "qa_analyser_iteration":   0,
        "status":                  "running",
        "project_dir":             None,
        "spec_dir":                None,
        "definition_of_done":      [],
        "needs_clarification":     False,
        "clarification_questions": [],
        "clarification_context":   "",
        "code_review_report":      None,
        "security_report":         None,
        "deploy_report":           None,
        "retrospective":           None,
        # Adaptive pipeline
        "pipeline_intent":         "feature",
        # SDD Speckit
        "constitution":            "",
        "spec_md":                 "",
        "plan_md":                 "",
        "tasks_md":                "",
        "checklist_md":            "",
        "spec_analysis":           None,
        "spec_revision_count":     0,
        # Multi-point interaction
        "user_message_queue":      [],
        "interaction_log":         [],
        "pause_requested":         False,
        **kwargs,
    }


# ── route_pm ──────────────────────────────────────────────────────────────────

def test_route_pm_no_clarification():
    state = _base_state(needs_clarification=False)
    assert route_pm(state) == "analyser"


def test_route_pm_needs_clarification():
    state = _base_state(needs_clarification=True, clarification_questions=["What stack?"])
    assert route_pm(state) == "clarification_gate"


# ── route_reviewer ────────────────────────────────────────────────────────────

def test_route_reviewer_pass():
    state = _base_state(code_review_report={"status": "pass", "issues": [], "summary": "LGTM"})
    assert route_reviewer(state) == "security"


def test_route_reviewer_no_report():
    state = _base_state(code_review_report=None)
    assert route_reviewer(state) == "security"


def test_route_reviewer_fail_under_limit():
    state = _base_state(
        iteration=1,
        code_review_report={"status": "fail", "issues": [{"file": "x.py", "line": 1, "severity": "major", "description": "bug"}], "summary": "issues found"},
    )
    assert route_reviewer(state) == "engineer"


def test_route_reviewer_fail_at_limit():
    state = _base_state(
        iteration=3,
        code_review_report={"status": "fail", "issues": [], "summary": "still failing"},
    )
    assert route_reviewer(state) == "retrospective"


# ── route_security ────────────────────────────────────────────────────────────

def test_route_security_pass():
    state = _base_state(security_report={"status": "pass", "vulnerabilities": [], "summary": "clean"})
    assert route_security(state) == "qa"


def test_route_security_warn():
    state = _base_state(security_report={"status": "warn", "vulnerabilities": [], "summary": "minor findings"})
    assert route_security(state) == "qa"  # warn is pass-through


def test_route_security_fail():
    state = _base_state(security_report={"status": "fail", "vulnerabilities": [{"tool": "bandit", "id": "B101", "severity": "HIGH", "description": "exec", "file": "x.py"}], "summary": "critical vuln"})
    assert route_security(state) == "retrospective"


def test_route_security_no_report():
    state = _base_state(security_report=None)
    assert route_security(state) == "qa"


# ── route_qa ──────────────────────────────────────────────────────────────────

def test_route_qa_pass():
    state = _base_state(test_report={"status": "pass", "summary": "", "passed": [], "failed": [], "defects": []})
    assert route_qa(state) == "deploy"


def test_route_qa_fail_minor_under_limit():
    state = _base_state(
        iteration=1,
        test_report={"status": "fail-minor", "summary": "", "passed": [], "failed": ["t1"], "defects": []},
    )
    assert route_qa(state) == "engineer"


def test_route_qa_fail_minor_at_limit():
    state = _base_state(
        iteration=3,
        test_report={"status": "fail-minor", "summary": "", "passed": [], "failed": ["t1"], "defects": []},
    )
    assert route_qa(state) == "retrospective"


def test_route_qa_fail_major_under_limit():
    state = _base_state(
        qa_analyser_iteration=1,
        test_report={"status": "fail-major", "summary": "", "passed": [], "failed": [], "defects": []},
    )
    assert route_qa(state) == "analyser"


def test_route_qa_fail_major_at_limit():
    state = _base_state(
        qa_analyser_iteration=2,
        test_report={"status": "fail-major", "summary": "", "passed": [], "failed": [], "defects": []},
    )
    assert route_qa(state) == "retrospective"


def test_route_qa_none_report():
    state = _base_state(test_report=None)
    assert route_qa(state) == "retrospective"


# ── route_retrospective ───────────────────────────────────────────────────────

def test_route_retrospective_deploy_pass():
    state = _base_state(deploy_report={"status": "pass", "endpoint": "http://localhost:9000", "response": "200", "command_used": "uvicorn"})
    assert route_retrospective(state) == "done"


def test_route_retrospective_deploy_fail():
    state = _base_state(deploy_report={"status": "fail", "endpoint": "", "response": "timeout", "command_used": "uvicorn"})
    assert route_retrospective(state) == "failed"


def test_route_retrospective_no_deploy_report():
    state = _base_state(deploy_report=None)
    assert route_retrospective(state) == "failed"


# ── Terminal nodes ────────────────────────────────────────────────────────────

def test_handle_done_sets_status(tmp_path):
    project_dir = tmp_path / "proj"
    (project_dir / "spec").mkdir(parents=True)
    state = _base_state(project_dir=str(project_dir))
    result = handle_done(state)
    assert result["status"] == "done"


def test_handle_failed_sets_status(tmp_path):
    project_dir = tmp_path / "proj"
    (project_dir / "spec").mkdir(parents=True)
    state = _base_state(project_dir=str(project_dir))
    result = handle_failed(state)
    assert result["status"] == "failed"


# ── Agent parse_submit ────────────────────────────────────────────────────────

def test_pm_parse_submit_basic():
    from agents.pm import PMAgent
    agent = PMAgent()
    state = _base_state()
    tasks = [{"id": "T1", "title": "Create schema", "description": "...", "priority": 1, "status": "pending"}]
    result = agent.parse_submit(state, {"tasks": tasks, "definition_of_done": ["DoD1"], "needs_clarification": False, "clarification_questions": []})
    assert result["tasks"] == tasks
    assert result["definition_of_done"] == ["DoD1"]
    assert result["needs_clarification"] is False


def test_pm_parse_submit_with_clarification():
    from agents.pm import PMAgent
    agent = PMAgent()
    state = _base_state()
    result = agent.parse_submit(state, {
        "tasks": [],
        "definition_of_done": [],
        "needs_clarification": True,
        "clarification_questions": ["What database?", "REST or GraphQL?"],
    })
    assert result["needs_clarification"] is True
    assert len(result["clarification_questions"]) == 2


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


def test_reviewer_parse_submit():
    from agents.reviewer import CodeReviewerAgent
    agent = CodeReviewerAgent()
    state = _base_state()
    report = {"status": "pass", "issues": [], "summary": "LGTM"}
    result = agent.parse_submit(state, report)
    assert result["code_review_report"]["status"] == "pass"


def test_security_parse_submit():
    from agents.security import SecurityAgent
    agent = SecurityAgent()
    state = _base_state()
    report = {"status": "warn", "vulnerabilities": [], "summary": "low-severity only"}
    result = agent.parse_submit(state, report)
    assert result["security_report"]["status"] == "warn"


def test_deploy_parse_submit():
    from agents.deploy import DeployAgent
    agent = DeployAgent()
    state = _base_state()
    report = {"status": "pass", "endpoint": "http://localhost:9000", "response": "200 OK", "command_used": "uvicorn app:main"}
    result = agent.parse_submit(state, report)
    assert result["deploy_report"]["status"] == "pass"


def test_retrospective_parse_submit():
    from agents.retrospective import RetrospectiveAgent
    agent = RetrospectiveAgent()
    state = _base_state()
    report = {"what_worked": ["good spec"], "what_failed": [], "lessons": ["be more specific"], "metrics": {}}
    result = agent.parse_submit(state, report)
    assert result["retrospective"]["what_worked"] == ["good spec"]


# ── route_analyser ────────────────────────────────────────────────────────────

def test_route_analyser_query():
    state = _base_state(pipeline_intent="query")
    assert route_analyser(state) == "done"


def test_route_analyser_test():
    state = _base_state(pipeline_intent="test")
    assert route_analyser(state) == "qa"


def test_route_analyser_review():
    state = _base_state(pipeline_intent="review")
    assert route_analyser(state) == "reviewer"


def test_route_analyser_bug_fix():
    state = _base_state(pipeline_intent="bug_fix")
    assert route_analyser(state) == "engineer"


def test_route_analyser_feature():
    state = _base_state(pipeline_intent="feature")
    assert route_analyser(state) == "spec_analyze"


def test_route_analyser_default():
    state = _base_state()  # default intent = "feature"
    assert route_analyser(state) == "spec_analyze"


# ── route_spec_analyze ────────────────────────────────────────────────────────

def test_route_spec_analyze_approved():
    state = _base_state(spec_analysis={"findings": [], "summary": "clean", "approved": True})
    assert route_spec_analyze(state) == "task_decompose"


def test_route_spec_analyze_not_approved_under_limit():
    state = _base_state(
        spec_revision_count=0,
        spec_analysis={"findings": [{"pass_name": "ambiguity", "severity": "HIGH", "location": "§1", "description": "vague", "suggestion": "be specific"}], "summary": "needs revision", "approved": False},
    )
    assert route_spec_analyze(state) == "analyser"


def test_route_spec_analyze_not_approved_at_limit():
    state = _base_state(
        spec_revision_count=2,
        spec_analysis={"findings": [], "summary": "still failing", "approved": False},
    )
    assert route_spec_analyze(state) == "retrospective"


def test_route_spec_analyze_no_report():
    # None analysis → not approved → revision_count=0 < MAX → retry analyser
    state = _base_state(spec_analysis=None, spec_revision_count=0)
    assert route_spec_analyze(state) == "analyser"


# ── route_qa intent routing ───────────────────────────────────────────────────

def test_route_qa_pass_test_intent():
    """test intent skips deploy — goes directly to done."""
    state = _base_state(
        pipeline_intent="test",
        test_report={"status": "pass", "summary": "", "passed": [], "failed": [], "defects": []},
    )
    assert route_qa(state) == "done"


def test_route_qa_pass_bug_fix_intent():
    """bug_fix intent skips deploy — goes directly to done."""
    state = _base_state(
        pipeline_intent="bug_fix",
        test_report={"status": "pass", "summary": "", "passed": [], "failed": [], "defects": []},
    )
    assert route_qa(state) == "done"


def test_route_qa_pass_feature_intent():
    """feature intent always deploys."""
    state = _base_state(
        pipeline_intent="feature",
        test_report={"status": "pass", "summary": "", "passed": [], "failed": [], "defects": []},
    )
    assert route_qa(state) == "deploy"


# ── route_reviewer intent routing ─────────────────────────────────────────────

def test_route_reviewer_review_intent_done():
    """review intent always terminates after reviewer."""
    state = _base_state(
        pipeline_intent="review",
        code_review_report={"status": "fail", "issues": [], "summary": "issues"},
    )
    assert route_reviewer(state) == "done"


# ── New agents parse_submit ───────────────────────────────────────────────────

def test_spec_analyze_parse_submit():
    from agents.spec_analyze import SpecAnalyzeAgent
    agent = SpecAnalyzeAgent()
    state = _base_state()
    report = {
        "findings": [{"pass_name": "ambiguity", "severity": "MEDIUM", "location": "§2", "description": "unclear", "suggestion": "specify"}],
        "summary": "1 MEDIUM finding",
        "approved": True,
    }
    result = agent.parse_submit(state, report)
    assert result["spec_analysis"]["approved"] is True
    assert len(result["spec_analysis"]["findings"]) == 1


# ── Regression: analyser spec_md must not be overwritten by plan_md ──────────

def test_analyser_spec_md_not_overwritten_by_plan_md():
    """Regression test: analyser.parse_submit must not overwrite spec_md with plan_md.
    Bug was: 'spec_md': data.get('plan_md', ...) — plan_md value was stored as spec_md."""
    from agents.analyser import AnalyserAgent
    agent = AnalyserAgent()
    state = _base_state(spec_md="original spec content", plan_md="original plan content")
    data = {
        "spec_md":  "new spec content",
        "plan_md":  "new plan content",
        "overview": "test overview",
        "components": [],
        "api_contracts": [],
        "data_models": [],
        "risks": [],
        "acceptance_criteria": [],
    }
    result = agent.parse_submit(state, data)
    assert result["spec_md"] == "new spec content", \
        "spec_md must come from data['spec_md'], not data['plan_md']"
    assert result["plan_md"] == "new plan content"


def test_analyser_spec_md_falls_back_to_state():
    """When agent returns no spec_md, the existing state value must be preserved."""
    from agents.analyser import AnalyserAgent
    agent = AnalyserAgent()
    state = _base_state(spec_md="preserved spec", plan_md="")
    data = {"plan_md": "some plan"}  # no spec_md key
    result = agent.parse_submit(state, data)
    assert result["spec_md"] == "preserved spec"


# ── Regression: spec_analyze server-side approval validation ─────────────────

def test_spec_analyze_critical_finding_overrides_approved_true():
    """Agent claiming approved=True with a CRITICAL finding must be rejected server-side."""
    from agents.spec_analyze import SpecAnalyzeAgent
    agent = SpecAnalyzeAgent()
    state = _base_state()
    data = {
        "findings": [{
            "pass_name": "coverage",
            "severity":  "CRITICAL",
            "location":  "spec.md §1",
            "description": "Missing auth entirely",
            "suggestion":  "Add auth section",
        }],
        "summary":  "1 CRITICAL finding",
        "approved": True,  # agent lies — should be overridden
    }
    result = agent.parse_submit(state, data)
    assert result["spec_analysis"]["approved"] is False, \
        "CRITICAL finding must force approved=False regardless of agent output"


def test_spec_analyze_high_finding_overrides_approved_true():
    """HIGH severity is also blocking."""
    from agents.spec_analyze import SpecAnalyzeAgent
    agent = SpecAnalyzeAgent()
    state = _base_state()
    data = {
        "findings": [{"pass_name": "ambiguity", "severity": "HIGH", "location": "§2", "description": "vague", "suggestion": "clarify"}],
        "summary":  "1 HIGH finding",
        "approved": True,
    }
    result = agent.parse_submit(state, data)
    assert result["spec_analysis"]["approved"] is False


def test_spec_analyze_medium_only_allows_approval():
    """MEDIUM/LOW findings must not block approval when agent says approved=True."""
    from agents.spec_analyze import SpecAnalyzeAgent
    agent = SpecAnalyzeAgent()
    state = _base_state()
    data = {
        "findings": [{"pass_name": "ambiguity", "severity": "MEDIUM", "location": "§2", "description": "minor", "suggestion": "clarify"}],
        "summary":  "1 MEDIUM finding",
        "approved": True,
    }
    result = agent.parse_submit(state, data)
    assert result["spec_analysis"]["approved"] is True


def test_spec_analyze_zero_findings_approved():
    """Zero findings with approved=True → approved."""
    from agents.spec_analyze import SpecAnalyzeAgent
    agent = SpecAnalyzeAgent()
    state = _base_state()
    data = {"findings": [], "summary": "All clear", "approved": True}
    result = agent.parse_submit(state, data)
    assert result["spec_analysis"]["approved"] is True


# ── task_decompose cycle detection ───────────────────────────────────────────

def test_task_decompose_acyclic_passes():
    from agents.task_decompose import _detect_cycle
    tasks = [
        {"id": "T1.1", "title": "A", "description": "", "phase": "Setup",       "priority": 1, "status": "pending", "depends_on": [],       "parallel": False},
        {"id": "T2.1", "title": "B", "description": "", "phase": "Foundation",  "priority": 1, "status": "pending", "depends_on": ["T1.1"], "parallel": False},
        {"id": "T3.1", "title": "C", "description": "", "phase": "Stories",     "priority": 1, "status": "pending", "depends_on": ["T2.1"], "parallel": False},
    ]
    assert _detect_cycle(tasks) is None


def test_task_decompose_direct_cycle_detected():
    """A → B → A is a direct 2-node cycle."""
    from agents.task_decompose import _detect_cycle
    tasks = [
        {"id": "T1.1", "title": "A", "description": "", "phase": "Setup",      "priority": 1, "status": "pending", "depends_on": ["T1.2"], "parallel": False},
        {"id": "T1.2", "title": "B", "description": "", "phase": "Foundation", "priority": 1, "status": "pending", "depends_on": ["T1.1"], "parallel": False},
    ]
    cycle = _detect_cycle(tasks)
    assert cycle is not None
    assert len(cycle) >= 2


def test_task_decompose_self_cycle_detected():
    """T1.1 depends on itself."""
    from agents.task_decompose import _detect_cycle
    tasks = [
        {"id": "T1.1", "title": "A", "description": "", "phase": "Setup", "priority": 1, "status": "pending", "depends_on": ["T1.1"], "parallel": False},
    ]
    cycle = _detect_cycle(tasks)
    assert cycle is not None


def test_task_decompose_three_node_cycle_detected():
    """A → B → C → A."""
    from agents.task_decompose import _detect_cycle
    tasks = [
        {"id": "T1.1", "title": "A", "description": "", "phase": "Setup",      "priority": 1, "status": "pending", "depends_on": ["T1.3"], "parallel": False},
        {"id": "T1.2", "title": "B", "description": "", "phase": "Foundation", "priority": 1, "status": "pending", "depends_on": ["T1.1"], "parallel": False},
        {"id": "T1.3", "title": "C", "description": "", "phase": "Stories",    "priority": 1, "status": "pending", "depends_on": ["T1.2"], "parallel": False},
    ]
    assert _detect_cycle(tasks) is not None


def test_task_decompose_parse_submit_raises_on_cycle():
    """parse_submit must raise ValueError when cycle is present."""
    from agents.task_decompose import TaskDecomposeAgent
    agent = TaskDecomposeAgent()
    state = _base_state()
    data = {
        "tasks": [
            {"id": "T1.1", "title": "A", "description": "", "phase": "Setup",      "priority": 1, "status": "pending", "depends_on": ["T1.2"], "parallel": False},
            {"id": "T1.2", "title": "B", "description": "", "phase": "Foundation", "priority": 1, "status": "pending", "depends_on": ["T1.1"], "parallel": False},
        ],
        "tasks_md": "",
        "summary":  "cycle",
    }
    with pytest.raises(ValueError, match="cycle"):
        agent.parse_submit(state, data)


# ── handle_done / handle_failed — queue drain ────────────────────────────────

def test_handle_done_drains_message_queue(tmp_path):
    project_dir = tmp_path / "proj"
    (project_dir / "spec").mkdir(parents=True)
    state = _base_state(
        project_dir=str(project_dir),
        user_message_queue=[{"from_user": "hello", "target_agent": "analyser", "timestamp": "t", "job_id": "j"}],
    )
    result = handle_done(state)
    assert result["status"] == "done"
    assert result["user_message_queue"] == []


def test_handle_failed_drains_message_queue(tmp_path):
    project_dir = tmp_path / "proj"
    (project_dir / "spec").mkdir(parents=True)
    state = _base_state(
        project_dir=str(project_dir),
        user_message_queue=[{"from_user": "stale", "target_agent": "pm", "timestamp": "t", "job_id": "j"}],
    )
    result = handle_failed(state)
    assert result["status"] == "failed"
    assert result["user_message_queue"] == []


# ── Message queue draining ────────────────────────────────────────────────────

def test_analyser_drains_own_messages():
    from agents.analyser import AnalyserAgent
    agent = AnalyserAgent()
    state = _base_state(user_message_queue=[
        {"from_user": "add auth", "target_agent": "analyser", "timestamp": "t", "job_id": "j"},
        {"from_user": "add tests", "target_agent": "qa",       "timestamp": "t", "job_id": "j"},
    ])
    data = {"spec_md": "", "plan_md": "", "overview": "", "components": [], "api_contracts": [], "data_models": [], "risks": [], "acceptance_criteria": []}
    result = agent.parse_submit(state, data)
    remaining = result["user_message_queue"]
    assert all(m["target_agent"] != "analyser" for m in remaining), \
        "analyser messages must be drained after parse_submit"
    assert any(m["target_agent"] == "qa" for m in remaining), \
        "messages for other agents must be preserved"


def test_task_decompose_parse_submit():
    from agents.task_decompose import TaskDecomposeAgent
    agent = TaskDecomposeAgent()
    state = _base_state()
    tasks = [
        {"id": "T1.1", "title": "Setup", "description": "init", "phase": "Setup",
         "priority": 1, "status": "pending", "depends_on": [], "parallel": False},
    ]
    result = agent.parse_submit(state, {"tasks": tasks, "tasks_md": "# Tasks\n- T1.1", "summary": "1 task"})
    assert len(result["tasks"]) == 1
    assert result["tasks"][0]["phase"] == "Setup"
    assert result["tasks_md"] == "# Tasks\n- T1.1"


def test_pm_parse_submit_intent_classification():
    from agents.pm import PMAgent
    agent = PMAgent()
    state = _base_state()
    result = agent.parse_submit(state, {
        "pipeline_intent": "query",
        "tasks": [],
        "definition_of_done": [],
        "needs_clarification": False,
        "clarification_questions": [],
        "constitution": "",
        "spec_md": "",
    })
    assert result["pipeline_intent"] == "query"


def test_task_decompose_drains_user_message_queue():
    from agents.task_decompose import TaskDecomposeAgent
    agent = TaskDecomposeAgent()
    queue = [
        {"from_user": "use PostgreSQL", "target_agent": "task_decompose", "timestamp": "2026-01-01T00:00:00Z", "job_id": "test-001"},
        {"from_user": "use REST API", "target_agent": "engineer", "timestamp": "2026-01-01T00:00:00Z", "job_id": "test-001"},
    ]
    state = _base_state(user_message_queue=queue)
    result = agent.parse_submit(state, {"tasks": [], "tasks_md": "", "summary": ""})
    remaining = result["user_message_queue"]
    assert len(remaining) == 1
    assert remaining[0]["target_agent"] == "engineer"


# ── _detect_cycle: dangling dependency reference ──────────────────────────────

def test_task_decompose_dangling_dependency_is_ignored():
    """A depends_on pointing to a non-existent task ID must not raise or detect a cycle."""
    from agents.task_decompose import _detect_cycle
    tasks = [
        {"id": "T1.1", "title": "A", "description": "", "phase": "Setup",
         "priority": 1, "status": "pending", "depends_on": ["T0.0"], "parallel": False},
    ]
    assert _detect_cycle(tasks) is None


def test_task_decompose_mixed_valid_and_dangling():
    """Dangling reference alongside a valid acyclic dependency — still no cycle."""
    from agents.task_decompose import _detect_cycle
    tasks = [
        {"id": "T1.1", "title": "A", "description": "", "phase": "Setup",
         "priority": 1, "status": "pending", "depends_on": ["GHOST"],  "parallel": False},
        {"id": "T1.2", "title": "B", "description": "", "phase": "Setup",
         "priority": 1, "status": "pending", "depends_on": ["T1.1"],   "parallel": False},
    ]
    assert _detect_cycle(tasks) is None


# ── handle_done/failed: drained messages added to interaction_log ─────────────

def test_handle_done_logs_drained_messages(tmp_path):
    """Drained queue messages must appear in interaction_log with drained_at=terminal."""
    project_dir = tmp_path / "proj"
    (project_dir / "spec").mkdir(parents=True)
    msg = {"from_user": "stale msg", "target_agent": "qa", "timestamp": "t", "job_id": "j"}
    state = _base_state(project_dir=str(project_dir), user_message_queue=[msg], interaction_log=[])
    result = handle_done(state)
    assert result["user_message_queue"] == []
    assert any(m.get("drained_at") == "terminal" for m in result["interaction_log"])


def test_handle_failed_logs_drained_messages(tmp_path):
    project_dir = tmp_path / "proj"
    (project_dir / "spec").mkdir(parents=True)
    msg = {"from_user": "late msg", "target_agent": "engineer", "timestamp": "t", "job_id": "j"}
    state = _base_state(project_dir=str(project_dir), user_message_queue=[msg], interaction_log=[])
    result = handle_failed(state)
    assert result["user_message_queue"] == []
    assert any(m.get("drained_at") == "terminal" for m in result["interaction_log"])


def test_handle_done_empty_queue_leaves_log_unchanged(tmp_path):
    """Empty queue must not touch interaction_log."""
    project_dir = tmp_path / "proj"
    (project_dir / "spec").mkdir(parents=True)
    existing_log = [{"from_user": "earlier msg", "target_agent": "pm", "drained_at": "terminal"}]
    state = _base_state(project_dir=str(project_dir), user_message_queue=[], interaction_log=existing_log)
    result = handle_done(state)
    assert result["interaction_log"] == existing_log


# ── ClaudeCodeBackend: retry path ────────────────────────────────────────────

async def test_backend_retries_on_nonzero_exit():
    """ClaudeCodeBackend retries once on non-zero exit, then succeeds."""
    from orchestrator.backends.claude_code_backend import ClaudeCodeBackend

    backend = ClaudeCodeBackend()
    state   = _base_state()

    attempt = 0

    async def fake_subprocess(cmd, env, cwd, stdin_data=None, timeout=None):
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            return b"", b"transient connection error", 1   # first attempt: non-zero exit
        # Second attempt: valid PM submit block
        payload = json.dumps({
            "result": (
                '<submit>{"tasks": [], "definition_of_done": ["All done"],'
                ' "needs_clarification": false, "clarification_questions": [],'
                ' "pipeline_intent": "feature", "constitution": "", "spec_md": ""}'
                "</submit>"
            ),
            "usage": {"input_tokens": 120, "output_tokens": 60},
        })
        return payload.encode(), b"", 0

    with patch("orchestrator.backends.claude_code_backend._run_subprocess", new=fake_subprocess):
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await backend.run("pm", state)

    assert attempt == 2, "should have retried exactly once"
    mock_sleep.assert_called_once_with(5)
    assert result["definition_of_done"] == ["All done"]


async def test_backend_raises_after_all_retries_exhausted():
    """If all retry attempts fail, the last exception is raised."""
    from orchestrator.backends.claude_code_backend import ClaudeCodeBackend

    backend = ClaudeCodeBackend()
    state   = _base_state()

    async def always_fails(cmd, env, cwd, stdin_data=None, timeout=None):
        return b"", b"persistent failure", 1

    with patch("orchestrator.backends.claude_code_backend._run_subprocess", new=always_fails):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="persistent failure"):
                await backend.run("pm", state)


async def test_backend_cost_uses_both_input_and_output_tokens():
    """cost_estimate_usd must reflect input + output token pricing, not output-only."""
    from orchestrator.backends.claude_code_backend import ClaudeCodeBackend

    backend = ClaudeCodeBackend()
    state   = _base_state()

    async def fake_subprocess(cmd, env, cwd, stdin_data=None, timeout=None):
        payload = json.dumps({
            "result": (
                '<submit>{"tasks": [], "definition_of_done": [],'
                ' "needs_clarification": false, "clarification_questions": [],'
                ' "pipeline_intent": "query", "constitution": "", "spec_md": ""}'
                "</submit>"
            ),
            # Haiku: in=$0.0008/1K, out=$0.00125/1K
            # 1000 in → $0.0008,  1000 out → $0.00125 → total = $0.00205
            "usage": {"input_tokens": 1000, "output_tokens": 1000},
        })
        return payload.encode(), b"", 0

    with patch("orchestrator.backends.claude_code_backend._run_subprocess", new=fake_subprocess):
        with patch("orchestrator.backends.claude_code_backend._get_model", return_value="claude-haiku-4-5-20251001"):
            result = await backend.run("pm", state)

    cost = result.get("cost_estimate_usd", 0.0)
    expected = (1000 / 1000 * 0.0008) + (1000 / 1000 * 0.00125)  # $0.00205
    assert abs(cost - expected) < 1e-7, f"expected ${expected:.6f} got ${cost:.6f}"
