"""
Query LangGraph checkpoint table to build project/run history.

LangGraph stores all state in the `checkpoints` table:
  checkpoints(thread_id, checkpoint_ns, checkpoint_id, type, checkpoint, metadata)

We query the LATEST checkpoint per thread_id to reconstruct run summaries,
then group by project_name (derived from project_dir basename).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Optional

from api.schemas import ProjectSummary, RunSummary

log = logging.getLogger(__name__)

_DB_URL: Optional[str] = os.environ.get("DATABASE_URL")


async def _get_pool():
    """Return an asyncpg connection pool for direct DB queries."""
    import asyncpg  # type: ignore
    return await asyncpg.create_pool(_DB_URL, min_size=1, max_size=3)


def _extract_channel_value(checkpoint_data: dict, key: str, default=None):
    """Safely extract a value from LangGraph's nested checkpoint structure."""
    try:
        cv = checkpoint_data.get("channel_values", {})
        return cv.get(key, default)
    except Exception:
        return default


def _derive_project_name(project_dir: Optional[str]) -> str:
    if not project_dir:
        return "no-project"
    return os.path.basename(project_dir.rstrip("/\\")) or "no-project"


def _parse_checkpoint(row: dict) -> Optional[RunSummary]:
    """Parse a single LangGraph checkpoint row into a RunSummary."""
    try:
        thread_id: str = row["thread_id"]

        # LangGraph stores checkpoint as JSON bytes or string
        raw = row["checkpoint"]
        if isinstance(raw, (bytes, memoryview)):
            raw = bytes(raw).decode()
        if isinstance(raw, str):
            data: dict = json.loads(raw)
        else:
            data = raw or {}

        channel_values = data.get("channel_values", {})

        status = channel_values.get("status", "unknown")
        request = channel_values.get("request", "")
        project_dir = channel_values.get("project_dir")
        pipeline_intent = channel_values.get("pipeline_intent", "feature")
        tasks = channel_values.get("tasks") or []

        # created_at: use row timestamp if available
        created_at = ""
        if row.get("created_at"):
            ts = row["created_at"]
            if isinstance(ts, datetime):
                created_at = ts.isoformat()
            else:
                created_at = str(ts)

        project_name = _derive_project_name(project_dir)
        request_snippet = str(request)[:100] if request else ""

        return RunSummary(
            job_id=thread_id,
            project_name=project_name,
            pipeline_intent=pipeline_intent,
            status=status,
            created_at=created_at,
            request_snippet=request_snippet,
            task_count=len(tasks) if isinstance(tasks, list) else 0,
        )
    except Exception as exc:
        log.warning("Failed to parse checkpoint row %s: %s", row.get("thread_id"), exc)
        return None


async def list_all_runs() -> list[RunSummary]:
    """Return one RunSummary per thread_id (latest checkpoint per thread)."""
    if not _DB_URL:
        return []
    pool = None
    try:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT ON (thread_id)
                    thread_id,
                    checkpoint,
                    created_at
                FROM checkpoints
                WHERE checkpoint_ns = ''
                ORDER BY thread_id, created_at DESC
            """)
        results = []
        for row in rows:
            run = _parse_checkpoint(dict(row))
            if run is not None:
                results.append(run)
        # Sort newest first
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results
    except Exception as exc:
        log.warning("list_all_runs failed: %s", exc)
        return []
    finally:
        if pool:
            await pool.close()


def group_by_project(runs: list[RunSummary]) -> list[ProjectSummary]:
    """Group RunSummary list into ProjectSummary list, sorted by last_updated DESC."""
    from collections import defaultdict
    groups: dict[str, list[RunSummary]] = defaultdict(list)
    for run in runs:
        groups[run.project_name].append(run)

    projects: list[ProjectSummary] = []
    for name, group_runs in groups.items():
        sorted_runs = sorted(group_runs, key=lambda r: r.created_at, reverse=True)
        projects.append(ProjectSummary(
            project_name=name,
            latest_run=sorted_runs[0].job_id,
            run_count=len(sorted_runs),
            last_updated=sorted_runs[0].created_at,
            status=sorted_runs[0].status,
        ))

    projects.sort(key=lambda p: p.last_updated, reverse=True)
    return projects
