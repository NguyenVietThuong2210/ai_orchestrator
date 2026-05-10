from __future__ import annotations

from typing import TypedDict, Optional


class Task(TypedDict):
    id: str
    title: str
    description: str
    priority: int          # 1 (highest) → 5 (lowest)
    status: str            # "pending" | "in_progress" | "done"


class TechnicalSpec(TypedDict):
    overview: str
    components: list[dict]
    api_contracts: list[dict]
    data_models: list[dict]
    risks: list[dict]
    acceptance_criteria: list[str]


class QAReport(TypedDict):
    status: str            # "pass" | "fail-minor" | "fail-major"
    summary: str
    passed: list[str]
    failed: list[str]
    defects: list[dict]    # [{id, severity, description, file, line}]


# Alias — QAReport is the canonical name; TestReport kept for backwards compat
TestReport = QAReport


class AgentEvent(TypedDict):
    agent: str
    timestamp: str
    status: str
    tokens_used: int
    duration_seconds: float
    note: str


class ProjectContext(TypedDict):
    request:                str
    job_id:                 str
    tasks:                  list[Task]
    spec:                   Optional[TechnicalSpec]
    artifact_paths:         dict[str, str]     # filename → local path or S3 key
    test_report:            Optional[TestReport]
    history:                list[AgentEvent]
    iteration:              int                # QA→Engineer retry count
    qa_analyser_iteration:  int                # QA→Analyser retry count
    status:                 str                # "running" | "done" | "failed"
    project_dir:            Optional[str]      # e.g. "projects/hello_django"
    spec_dir:               Optional[str]      # e.g. "projects/hello_django/spec"
