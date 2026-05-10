"""Pydantic I/O schemas for the FastAPI backend."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class RunPipelineRequest(BaseModel):
    requirement: str = Field(..., min_length=10, description="User requirement text")
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
    spec: Optional[dict]               # TechnicalSpec — needed by MCP project_spec resource
    test_report: Optional[dict]
    history: list[dict]                # AgentEvent list — needed by MCP agent_logs resource
    cost_estimate_usd: Optional[float]


class CancelJobResponse(BaseModel):
    job_id: str
    message: str
