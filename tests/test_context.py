"""Test ProjectContext TypedDict structure."""
from orchestrator.context import ProjectContext, Task, TechnicalSpec, TestReport


def _make_state() -> ProjectContext:
    return {
        "request":               "Build a todo REST API",
        "job_id":                "test-job-001",
        "tasks":                 [],
        "spec":                  None,
        "artifact_paths":        {},
        "test_report":           None,
        "history":               [],
        "iteration":             0,
        "qa_analyser_iteration": 0,
        "status":                "running",
    }


def test_initial_state_keys():
    state = _make_state()
    required_keys = {
        "request", "job_id", "tasks", "spec",
        "artifact_paths", "test_report", "history",
        "iteration", "qa_analyser_iteration", "status",
    }
    assert required_keys == set(state.keys())


def test_state_immutable_update():
    state   = _make_state()
    updated = {**state, "status": "done", "iteration": 1}
    assert state["status"] == "running"   # original unchanged
    assert updated["status"] == "done"
    assert updated["iteration"] == 1


def test_task_structure():
    task: Task = {
        "id":          "T1",
        "title":       "Create DB schema",
        "description": "Design and create the SQLite schema for todos",
        "priority":    1,
        "status":      "pending",
    }
    assert task["priority"] == 1
    assert task["status"] == "pending"


def test_test_report_statuses():
    for status in ("pass", "fail-minor", "fail-major"):
        report: TestReport = {
            "status":  status,
            "summary": "test",
            "passed":  [],
            "failed":  [],
            "defects": [],
        }
        assert report["status"] == status
