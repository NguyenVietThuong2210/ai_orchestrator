"""Pydantic I/O schemas for the FastAPI backend."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class RunPipelineRequest(BaseModel):
    requirement: str = Field(..., min_length=10, max_length=8000)
    job_id: Optional[str] = Field(None)


class RunPipelineResponse(BaseModel):
    job_id: str
    status: str
    message: str


class ApproveSpecRequest(BaseModel):
    job_id: str
    decision: str = Field("approve", pattern="^(approve|reject)$")


class ApproveSpecResponse(BaseModel):
    job_id: str
    status: str
    message: str


class ClarifyRequest(BaseModel):
    job_id: str
    clarification_context: str = Field(..., min_length=1, max_length=4000)


class ClarifyResponse(BaseModel):
    job_id: str
    status: str
    message: str


class InjectMessageRequest(BaseModel):
    """Inject a user message into the running pipeline's message queue."""
    message: str = Field(..., min_length=1, max_length=4000,
                         description="Message text to inject")
    target_agent: str = Field("any", description="Which agent should drain this ('any' = next agent)")


class InjectMessageResponse(BaseModel):
    job_id: str
    status: str
    message: str
    queue_length: int


class ModifySpecRequest(BaseModel):
    """Directly update spec_md or plan_md before the human gate resumes."""
    spec_md: Optional[str] = Field(None, max_length=32000)
    plan_md: Optional[str] = Field(None, max_length=32000)
    note: str = Field("", max_length=500, description="Reason for modification")


class ModifySpecResponse(BaseModel):
    job_id: str
    status: str
    message: str


class PauseRequest(BaseModel):
    """Request the pipeline to pause before the next agent node."""
    reason: str = Field("", max_length=500)


class PauseResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    current_node: str
    iteration: int
    qa_analyser_iteration: int
    artifact_paths: dict[str, str]
    tasks: list[dict]
    spec: Optional[dict]
    test_report: Optional[dict]
    history: list[dict]
    cost_estimate_usd: Optional[float]
    project_dir: Optional[str]
    spec_dir: Optional[str]
    error: Optional[str] = None
    # PM clarification
    definition_of_done: list[str] = []
    needs_clarification: bool = False
    clarification_questions: list[str] = []
    # Post-engineering reports
    code_review_report: Optional[dict] = None
    security_report: Optional[dict] = None
    deploy_report: Optional[dict] = None
    retrospective: Optional[dict] = None
    # Adaptive pipeline
    pipeline_intent: str = "feature"
    # SDD Speckit artifacts
    spec_md: str = ""
    plan_md: str = ""
    tasks_md: str = ""
    constitution: str = ""
    # Spec analysis
    spec_analysis: Optional[dict] = None
    spec_revision_count: int = 0
    # Multi-point interaction
    user_message_queue: list[dict] = []
    interaction_log: list[dict] = []


class ResumeJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class CancelJobResponse(BaseModel):
    job_id: str
    message: str


class JobSummary(BaseModel):
    job_id: str
    status: str


class JobListResponse(BaseModel):
    jobs: list[JobSummary]


# ── Project History ────────────────────────────────────────────────────────────

class RunSummary(BaseModel):
    job_id: str
    project_name: str
    pipeline_intent: str = "feature"
    status: str
    created_at: str
    request_snippet: str = ""
    task_count: int = 0


class ProjectSummary(BaseModel):
    project_name: str
    latest_run: str
    run_count: int
    last_updated: str
    status: str


class ProjectListResponse(BaseModel):
    projects: list[ProjectSummary]


class RunListResponse(BaseModel):
    project_name: str
    runs: list[RunSummary]
