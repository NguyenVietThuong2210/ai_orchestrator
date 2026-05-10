"""
Mode B backend — Claude Code sub-agents via `claude` CLI.

No ANTHROPIC_API_KEY needed: uses Pro subscription auth from the active Claude Code session.
Requires `claude` CLI installed and an active Claude Code session when the pipeline runs.

How it works:
  1. Each agent turn spawns `claude -p <prompt> --model <model>` as a subprocess
  2. The prompt = agent.build_prompt(state) + SUBMIT_INSTRUCTIONS (mode-B specific)
  3. We parse the <submit>...</submit> block and call agent.parse_submit(state, data)
  4. Engineer / QA agents run with cwd=ARTIFACT_DIR so file tools work naturally
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone

from orchestrator.backends.base import BaseBackend
from orchestrator.context import ProjectContext, AgentEvent

logger = logging.getLogger(__name__)


def _get_artifact_dir() -> str:
    return os.getenv("ARTIFACT_DIR", "./artifacts")


def _claude_cmd() -> str:
    """Return 'claude.cmd' on Windows (asyncio.create_subprocess_exec can't resolve .cmd
    via PATHEXT), plain 'claude' elsewhere."""
    return "claude.cmd" if os.name == "nt" else "claude"


def _get_model(agent_name: str) -> str:
    """Lazy model lookup — reads ENV at call time, after load_dotenv()."""
    defaults = {
        "pm":       "claude-haiku-4-5-20251001",
        "analyser": "claude-sonnet-4-6",
        "engineer": "claude-sonnet-4-6",
        "qa":       "claude-sonnet-4-6",
    }
    return os.getenv(f"{agent_name.upper()}_MODEL_B", defaults[agent_name])


# Mode-B specific submit instructions appended after the agent's own prompt
SUBMIT_INSTRUCTIONS: dict[str, str] = {
    "pm": """
---
Output your result at the very end as valid JSON inside <submit> tags:
<submit>
{
  "tasks": [
    {"id": "T1", "title": "...", "description": "...", "priority": 1, "status": "pending"}
  ]
}
</submit>""",

    "analyser": """
---
Output your result at the very end as valid JSON inside <submit> tags:
<submit>
{
  "overview": "...",
  "components": [...],
  "api_contracts": [...],
  "data_models": [...],
  "risks": [...],
  "acceptance_criteria": ["Given X when Y then Z"]
}
</submit>""",

    "engineer": """
---
After writing all files, output a <submit> block listing them:
<submit>
{
  "artifact_paths": {"filename.py": "./artifacts/filename.py"},
  "summary": "Brief description of what was implemented"
}
</submit>""",

    "qa": """
---
Output your TestReport at the very end as valid JSON inside <submit> tags:
<submit>
{
  "status": "pass",
  "summary": "...",
  "passed": ["test_name"],
  "failed": [],
  "defects": []
}
</submit>
Valid status values: "pass" | "fail-minor" | "fail-major"
""",
}


def _extract_submit_data(agent_name: str, output: str) -> dict:
    """Extract and parse the <submit>...</submit> JSON block from CLI output."""
    match = re.search(r"<submit>\s*(.*?)\s*</submit>", output, re.DOTALL)
    if not match:
        raise ValueError(
            f"[{agent_name}] No <submit> block found in output.\n"
            f"Raw output (last 500 chars):\n...{output[-500:]}"
        )
    return json.loads(match.group(1))


class ClaudeCodeBackend(BaseBackend):
    """
    Spawns each agent as a `claude -p` subprocess.

    - Auth:   Claude Code Pro session (no API key needed)
    - Model:  per-agent ENV override read lazily at call time
    - Prompt: agent.build_prompt(state) + SUBMIT_INSTRUCTIONS[agent_name]
    - Parse:  agent.parse_submit(state, data) — single source of truth
    - Tools:  Engineer / QA run with cwd=ARTIFACT_DIR so `claude` reads/writes files natively
    """

    async def run(self, agent_name: str, state: ProjectContext) -> ProjectContext:
        # Import here to avoid circular imports at module load time
        from agents import AGENTS

        agent = AGENTS[agent_name]
        model = _get_model(agent_name)

        # Build prompt: agent context + mode-B submit instructions
        prompt = agent.build_prompt(state) + SUBMIT_INSTRUCTIONS[agent_name]

        # Engineer and QA need filesystem access — run from ARTIFACT_DIR
        artifact_dir = _get_artifact_dir()
        cwd = artifact_dir if agent_name in ("engineer", "qa") else None
        if cwd:
            os.makedirs(cwd, exist_ok=True)

        logger.info("[%s] spawning claude subprocess (model=%s)", agent_name, model)
        start = datetime.now(timezone.utc)

        cmd = [
            _claude_cmd(),
            "--model", model,
            "-p", prompt,
            "--output-format", "json",
        ]

        # Unset CLAUDECODE so the subprocess isn't blocked by the nested-session guard
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        duration = (datetime.now(timezone.utc) - start).total_seconds()

        if proc.returncode != 0:
            err = stderr_bytes.decode(errors="replace")
            raise RuntimeError(
                f"[{agent_name}] claude subprocess exited {proc.returncode}:\n{err}"
            )

        raw = stdout_bytes.decode(errors="replace")

        # `--output-format json` wraps output: {"result": "...", "cost_usd": ..., "usage": {...}}
        try:
            envelope = json.loads(raw)
            text_output = envelope.get("result", raw)
            tokens      = envelope.get("usage", {}).get("output_tokens", 0)
        except json.JSONDecodeError:
            text_output = raw   # fallback: plain text (older CLI)
            tokens = 0

        logger.info("[%s] done in %.1fs, tokens=%d", agent_name, duration, tokens)

        # Parse submit block, then delegate state update to the agent
        data    = _extract_submit_data(agent_name, text_output)
        updated = agent.parse_submit(state, data)

        # Append audit event
        event: AgentEvent = {
            "agent":            agent_name,
            "timestamp":        start.isoformat(),
            "status":           "ok",
            "tokens_used":      tokens,
            "duration_seconds": duration,
            "note":             f"mode=claude_code model={model}",
        }
        updated["history"] = list(state.get("history", [])) + [event]

        return updated
