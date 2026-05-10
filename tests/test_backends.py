"""
Test ClaudeCodeBackend parsing logic without spawning a real subprocess.
All tests are offline — no claude CLI, no API calls.
"""
from __future__ import annotations

import json
import pytest

from orchestrator.context import ProjectContext
from orchestrator.backends.claude_code_backend import (
    SUBMIT_INSTRUCTIONS,
    _extract_submit_data,
    _get_model,
)
from agents import AGENTS


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


# ── Model selection ───────────────────────────────────────────────────────────

def test_get_model_defaults():
    assert _get_model("pm")       == "claude-haiku-4-5-20251001"
    assert _get_model("analyser") == "claude-sonnet-4-6"
    assert _get_model("engineer") == "claude-sonnet-4-6"
    assert _get_model("qa")       == "claude-sonnet-4-6"


def test_get_model_env_override(monkeypatch):
    monkeypatch.setenv("ANALYSER_MODEL_B", "claude-opus-4-7")
    assert _get_model("analyser") == "claude-opus-4-7"


# ── agent.build_prompt() ──────────────────────────────────────────────────────

def test_pm_build_prompt_includes_requirement():
    state  = _base_state()
    prompt = AGENTS["pm"].build_prompt(state)
    assert "Build a todo REST API" in prompt


def test_analyser_build_prompt_includes_tasks():
    state = _base_state(tasks=[
        {"id": "T1", "title": "Create schema", "description": "...", "priority": 1, "status": "pending"}
    ])
    prompt = AGENTS["analyser"].build_prompt(state)
    assert "T1" in prompt


def test_engineer_build_prompt_includes_spec():
    state = _base_state(spec={
        "overview": "Todo API overview",
        "components": [], "api_contracts": [], "data_models": [],
        "risks": [], "acceptance_criteria": [],
    })
    prompt = AGENTS["engineer"].build_prompt(state)
    assert "Todo API overview" in prompt


def test_engineer_build_prompt_includes_defects_on_retry():
    report = {
        "status": "fail-minor", "summary": "bad", "passed": [],
        "failed": ["test_create"],
        "defects": [{"id": "D1", "severity": "minor",
                     "description": "missing 404 handler", "file": "app.py", "line": 12}],
    }
    state  = _base_state(iteration=1, test_report=report)
    prompt = AGENTS["engineer"].build_prompt(state)
    assert "D1" in prompt
    assert "missing 404 handler" in prompt


def test_submit_instructions_appended():
    """Verify the full Mode-B prompt includes submit instructions."""
    state  = _base_state()
    prompt = AGENTS["pm"].build_prompt(state) + SUBMIT_INSTRUCTIONS["pm"]
    assert "<submit>" in prompt
    assert "tasks" in prompt


# ── _extract_submit_data ──────────────────────────────────────────────────────

def test_extract_submit_data_pm():
    output = 'Some analysis...\n<submit>\n{"tasks": [{"id":"T1","title":"x","description":"y","priority":1,"status":"pending"}]}\n</submit>'
    data   = _extract_submit_data("pm", output)
    assert data["tasks"][0]["id"] == "T1"


def test_extract_submit_data_analyser():
    spec   = {"overview": "API", "components": [], "api_contracts": [],
               "data_models": [], "risks": [], "acceptance_criteria": ["Given X when Y then Z"]}
    output = f"Analysis done.\n<submit>\n{json.dumps(spec)}\n</submit>"
    data   = _extract_submit_data("analyser", output)
    assert data["overview"] == "API"


def test_extract_submit_data_qa_pass():
    report = {"status": "pass", "summary": "All good", "passed": ["test_create"], "failed": [], "defects": []}
    output = f"QA done.\n<submit>\n{json.dumps(report)}\n</submit>"
    data   = _extract_submit_data("qa", output)
    assert data["status"] == "pass"


def test_extract_submit_missing_block_raises():
    with pytest.raises(ValueError, match="No <submit>"):
        _extract_submit_data("pm", "I forgot the submit block.")


def test_extract_submit_invalid_json_raises():
    with pytest.raises(json.JSONDecodeError):
        _extract_submit_data("pm", "<submit>\nnot valid json\n</submit>")


# ── agent.parse_submit() — single source of truth for state updates ───────────

def test_pm_parse_submit():
    state = _base_state()
    tasks = [{"id": "T1", "title": "Create schema", "description": "...", "priority": 1, "status": "pending"}]
    result = AGENTS["pm"].parse_submit(state, {"tasks": tasks})
    assert result["tasks"] == tasks


def test_analyser_parse_submit():
    state = _base_state()
    spec  = {"overview": "API", "components": [], "api_contracts": [],
              "data_models": [], "risks": [], "acceptance_criteria": []}
    result = AGENTS["analyser"].parse_submit(state, spec)
    assert result["spec"]["overview"] == "API"


def test_engineer_parse_submit():
    state = _base_state()
    data  = {"artifact_paths": {"app.py": "./artifacts/app.py"}, "summary": "done"}
    result = AGENTS["engineer"].parse_submit(state, data)
    assert result["artifact_paths"]["app.py"] == "./artifacts/app.py"


def test_qa_parse_submit_pass():
    state  = _base_state()
    result = AGENTS["qa"].parse_submit(state, {
        "status": "pass", "summary": "", "passed": ["t1"], "failed": [], "defects": []
    })
    assert result["test_report"]["status"] == "pass"
    assert result["iteration"] == 0


def test_qa_parse_submit_increments_iteration():
    state  = _base_state(iteration=1)
    result = AGENTS["qa"].parse_submit(state, {
        "status": "fail-minor", "summary": "", "passed": [], "failed": [], "defects": []
    })
    assert result["iteration"] == 2
    assert result["qa_analyser_iteration"] == 0


def test_qa_parse_submit_increments_analyser_iteration():
    state  = _base_state(qa_analyser_iteration=0)
    result = AGENTS["qa"].parse_submit(state, {
        "status": "fail-major", "summary": "", "passed": [], "failed": [], "defects": []
    })
    assert result["qa_analyser_iteration"] == 1
    assert result["iteration"] == 0
