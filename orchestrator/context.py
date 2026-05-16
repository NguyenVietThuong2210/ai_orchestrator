from __future__ import annotations

from typing import TypedDict, Optional


class Task(TypedDict):
    id: str
    title: str
    description: str
    priority: int          # 1 (highest) → 5 (lowest)
    status: str            # "pending" | "in_progress" | "done"
    phase: str             # "Setup" | "Foundation" | "Stories" | "Polish"
    depends_on: list[str]  # task IDs this task depends on
    parallel: bool         # True = can run in parallel with siblings


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


class CodeReviewReport(TypedDict):
    status: str            # "pass" | "fail"
    issues: list[dict]     # [{file, line, severity, description}]
    summary: str


class SecurityReport(TypedDict):
    status: str            # "pass" | "warn" | "fail"
    vulnerabilities: list[dict]  # [{tool, id, severity, description, file}]
    summary: str


class DeployReport(TypedDict):
    status: str            # "pass" | "fail"
    endpoint: str
    response: str
    command_used: str


class Retrospective(TypedDict):
    what_worked: list[str]
    what_failed: list[str]
    lessons: list[str]
    metrics: dict          # {total_agents, total_tokens, qa_retries, spec_retries}


class AgentEvent(TypedDict):
    agent: str
    timestamp: str
    status: str
    tokens_used: int
    duration_seconds: float
    note: str


class SpecAnalysisFinding(TypedDict):
    pass_name: str          # "duplication"|"ambiguity"|"underspecification"|"constitution"|"coverage"
    severity: str           # "CRITICAL"|"HIGH"|"MEDIUM"|"LOW"
    location: str           # e.g. "spec.md §3.2"
    description: str
    suggestion: str


class SpecAnalysisReport(TypedDict):
    findings: list[SpecAnalysisFinding]
    summary: str
    approved: bool          # True only if no CRITICAL/HIGH findings


class UserMessage(TypedDict):
    from_user: str          # raw user text
    target_agent: str       # which agent should drain this message ("any" = next agent)
    timestamp: str
    job_id: str


class ProjectContext(TypedDict):
    # ── Core ──────────────────────────────────────────────────────────────────
    request:                str
    job_id:                 str
    tasks:                  list[Task]
    spec:                   Optional[TechnicalSpec]
    artifact_paths:         dict[str, str]
    test_report:            Optional[TestReport]
    history:                list[AgentEvent]
    iteration:              int                # QA→Engineer retry count
    qa_analyser_iteration:  int                # QA→Analyser retry count
    status:                 str                # "running"|"waiting_approval"|"waiting_clarification"|"done"|"failed"
    project_dir:            Optional[str]
    spec_dir:               Optional[str]

    # ── PM clarification ──────────────────────────────────────────────────────
    definition_of_done:     list[str]
    needs_clarification:    bool
    clarification_questions: list[str]
    clarification_context:  str               # user's response to clarification

    # ── Post-engineering reports ───────────────────────────────────────────────
    code_review_report:     Optional[CodeReviewReport]
    security_report:        Optional[SecurityReport]
    deploy_report:          Optional[DeployReport]
    retrospective:          Optional[Retrospective]

    # ── Adaptive pipeline intent ───────────────────────────────────────────────
    # "query"   → PM classifies as a question; Analyser answers, done
    # "test"    → run QA only, no dev
    # "bug_fix" → Engineer patches, QA verifies
    # "feature" → full SDD Speckit pipeline
    # "review"  → Analyser + Reviewer only
    pipeline_intent:        str               # default "feature"

    # ── SDD Speckit artifacts (written to specs/ directory) ───────────────────
    constitution:           str               # specs/constitution.md — immutable project principles
    spec_md:                str               # specs/spec.md — speckit specify output
    plan_md:                str               # specs/plan.md — speckit plan output
    tasks_md:               str               # specs/tasks.md — speckit tasks output
    checklist_md:           str               # specs/checklist.md — definition-of-done checklist

    # ── Spec analysis ─────────────────────────────────────────────────────────
    spec_analysis:          Optional[SpecAnalysisReport]
    spec_revision_count:    int               # how many times spec was revised

    # ── Multi-point user interaction ──────────────────────────────────────────
    # Messages queued via POST /inject/{job_id}; drained by the next agent at node entry
    user_message_queue:     list[UserMessage]
    interaction_log:        list[dict]        # full history of injected messages + agent responses

    # ── Pause/resume control ──────────────────────────────────────────────────
    pause_requested:        bool              # set True by POST /pause/{job_id}
