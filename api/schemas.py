"""Pydantic I/O schemas for the FastAPI backend."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class RunPipelineRequest(BaseModel):
    requirement: str = Field(..., min_length=10, max_length=8000, description="User requirement text")
    job_id: Optional[str] = Field(None, description="Optional — provide to resume a previous job")


class RunPipelineResponse(BaseModel):
    job_id: str
    status: str   # "started" | "resumed"
    message: str


class ApproveSpecRequest(BaseModel):
    job_id: str
    decision: str = Field("approve", pattern="^(approve|reject)$")


class ApproveSpecResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str                        # "running" | "waiting_approval" | "done" | "failed"
    current_node: str
    iteration: int
    qa_analyser_iteration: int
    artifact_paths: dict[str, str]
    tasks: list[dict]                  # PM output — Task list
    spec: Optional[dict]               # TechnicalSpec — needed by MCP project_spec resource
    test_report: Optional[dict]
    history: list[dict]                # AgentEvent list — needed by MCP agent_logs resource
    cost_estimate_usd: Optional[float]
    project_dir: Optional[str]         # e.g. "projects/hello_django"
    spec_dir: Optional[str]            # e.g. "projects/hello_django/spec"
    error: Optional[str] = None        # error message when status="failed"


class ResumeJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class CancelJobResponse(BaseModel):
    job_id: str
    message: str


class JobSummary(BaseModel):
    job_id: str
    status: str   # last known status from _jobs registry


class JobListResponse(BaseModel):
    jobs: list[JobSummary]
