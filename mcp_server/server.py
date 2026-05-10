"""
FastMCP server — exposes the AI Orchestrator as MCP tools/resources/prompts.

VS Code / Claude Code connects via:
  stdio:  python mcp_server/server.py
  HTTP:   python mcp_server/server.py --transport http --port 8001

Routes through FastAPI backend (port 8000) — does not run the pipeline directly.
"""
from __future__ import annotations

import httpx
import os
from fastmcp import FastMCP

API_BASE = os.getenv("ORCHESTRATOR_API_URL", "http://localhost:8000")

mcp = FastMCP(
    name="ai-orchestrator",
    instructions="Tools to run the AI software development pipeline (PM → Analyser → Engineer → QA).",
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
    """Get the current status, iteration count, and artifacts of a pipeline job."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/status/{job_id}", timeout=10)
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def approve_spec(job_id: str, decision: str = "approve") -> dict:
    """
    Approve or reject the technical spec at the Human Gate.
    decision: "approve" (default) | "reject"
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_BASE}/approve-spec",
                              json={"job_id": job_id, "decision": decision}, timeout=30)
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
    import json
    return json.dumps(data.get("spec") or {}, indent=2, ensure_ascii=False)


@mcp.resource("test_report/{job_id}")
async def test_report(job_id: str) -> str:
    """Read the QA TestReport for a job."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/status/{job_id}", timeout=10)
        r.raise_for_status()
        data = r.json()
    import json
    return json.dumps(data.get("test_report") or {}, indent=2, ensure_ascii=False)


@mcp.resource("agent_logs/{job_id}")
async def agent_logs(job_id: str) -> str:
    """Read the full agent event history for a job."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/status/{job_id}", timeout=10)
        r.raise_for_status()
        data = r.json()
    import json
    return json.dumps(data.get("history") or [], indent=2, ensure_ascii=False)


# ── Prompts ───────────────────────────────────────────────────────────────────

@mcp.prompt()
def build_feature(feature_description: str) -> str:
    """Template for building a new feature end-to-end."""
    return (
        f"Use the run_pipeline tool to build this feature:\n\n"
        f"{feature_description}\n\n"
        "After it starts, poll get_job_status until status is 'waiting_approval', "
        "then review the spec and call approve_spec."
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
    """Template for checking QA results."""
    return (
        f"Read the test_report resource for job {job_id} "
        "and summarise: what passed, what failed, and severity of defects."
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
