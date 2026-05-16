"""
FastMCP server — exposes the AI Orchestrator as MCP tools/resources/prompts.

VS Code / Claude Code connects via:
  stdio:  python mcp_server/server.py
  HTTP:   python mcp_server/server.py --transport http --port 8001

Routes through FastAPI backend (port 8000) — does not run the pipeline directly.
"""
from __future__ import annotations

import httpx
import json
import os
from fastmcp import FastMCP

API_BASE = os.getenv("ORCHESTRATOR_API_URL", "http://localhost:8000")

mcp = FastMCP(
    name="ai-orchestrator",
    instructions=(
        "Tools to run the AI software development pipeline: "
        "PM → Analyser → Engineer → Reviewer → Security → QA → Deploy → Retrospective."
    ),
)


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def run_pipeline(requirement: str) -> dict:
    """
    Start a new AI pipeline run.
    Returns job_id — use get_job_status or approve_spec with this ID.
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_BASE}/run-pipeline",
                              json={"requirement": requirement}, timeout=30)
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def get_job_status(job_id: str) -> dict:
    """Get the current status, iteration count, and all agent reports for a pipeline job."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/status/{job_id}", timeout=10)
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def approve_spec(job_id: str, decision: str = "approve") -> dict:
    """
    Approve or reject the technical spec at the Human Gate.
    decision: "approve" (default) | "reject"
    Call this when get_job_status returns status == "waiting_approval".
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_BASE}/approve-spec",
                              json={"job_id": job_id, "decision": decision}, timeout=30)
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def clarify_job(job_id: str, answers: str) -> dict:
    """
    Submit answers to the PM's clarification questions and resume the pipeline.
    Call this when get_job_status returns status == "waiting_clarification".
    answers: plain text answering the PM's clarification_questions.
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{API_BASE}/clarify/{job_id}",
            json={"job_id": job_id, "clarification_context": answers},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def cancel_job(job_id: str) -> dict:
    """Cancel a running pipeline job."""
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_BASE}/cancel/{job_id}", timeout=10)
        r.raise_for_status()
        return r.json()


# ── Resources ─────────────────────────────────────────────────────────────────

@mcp.resource("project_spec/{job_id}")
async def project_spec(job_id: str) -> str:
    """Read the TechnicalSpec produced by the Analyser agent."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/status/{job_id}", timeout=10)
        r.raise_for_status()
        data = r.json()
    return json.dumps(data.get("spec") or {}, indent=2, ensure_ascii=False)


@mcp.resource("test_report/{job_id}")
async def test_report(job_id: str) -> str:
    """Read the QA TestReport for a job."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/status/{job_id}", timeout=10)
        r.raise_for_status()
        data = r.json()
    return json.dumps(data.get("test_report") or {}, indent=2, ensure_ascii=False)


@mcp.resource("code_review_report/{job_id}")
async def code_review_report(job_id: str) -> str:
    """Read the Code Review report produced by the Reviewer agent."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/status/{job_id}", timeout=10)
        r.raise_for_status()
        data = r.json()
    return json.dumps(data.get("code_review_report") or {}, indent=2, ensure_ascii=False)


@mcp.resource("security_report/{job_id}")
async def security_report(job_id: str) -> str:
    """Read the Security scan report (bandit + pip-audit) for a job."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/status/{job_id}", timeout=10)
        r.raise_for_status()
        data = r.json()
    return json.dumps(data.get("security_report") or {}, indent=2, ensure_ascii=False)


@mcp.resource("deploy_report/{job_id}")
async def deploy_report(job_id: str) -> str:
    """Read the Deploy & smoke-test report for a job."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/status/{job_id}", timeout=10)
        r.raise_for_status()
        data = r.json()
    return json.dumps(data.get("deploy_report") or {}, indent=2, ensure_ascii=False)


@mcp.resource("retrospective/{job_id}")
async def retrospective(job_id: str) -> str:
    """Read the Retrospective (lessons learned) report for a job."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/status/{job_id}", timeout=10)
        r.raise_for_status()
        data = r.json()
    return json.dumps(data.get("retrospective") or {}, indent=2, ensure_ascii=False)


@mcp.resource("agent_logs/{job_id}")
async def agent_logs(job_id: str) -> str:
    """Read the full agent event history for a job."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/status/{job_id}", timeout=10)
        r.raise_for_status()
        data = r.json()
    return json.dumps(data.get("history") or [], indent=2, ensure_ascii=False)


# ── Prompts ───────────────────────────────────────────────────────────────────

@mcp.prompt()
def build_feature(feature_description: str) -> str:
    """Template for building a new feature end-to-end."""
    return (
        f"Use the run_pipeline tool to build this feature:\n\n"
        f"{feature_description}\n\n"
        "Workflow:\n"
        "1. Call run_pipeline — get job_id\n"
        "2. Poll get_job_status until status changes\n"
        "3. If status == 'waiting_clarification': read clarification_questions, then call clarify_job with answers\n"
        "4. If status == 'waiting_approval': read the spec via project_spec resource, then call approve_spec\n"
        "5. Poll until status == 'done' or 'failed'\n"
        "6. Read retrospective resource for lessons learned\n"
    )


@mcp.prompt()
def review_spec(job_id: str) -> str:
    """Template for reviewing a spec before approving."""
    return (
        f"Read the spec for job {job_id} using the project_spec resource, "
        "review it carefully, then call approve_spec with job_id and your decision."
    )


@mcp.prompt()
def run_qa(job_id: str) -> str:
    """Template for checking all reports after pipeline completes."""
    return (
        f"For job {job_id}, read and summarise:\n"
        "- test_report: what passed, what failed, severity of defects\n"
        "- code_review_report: any code quality issues\n"
        "- security_report: any vulnerabilities found\n"
        "- deploy_report: whether the service started and passed smoke test\n"
        "- retrospective: key lessons learned\n"
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
