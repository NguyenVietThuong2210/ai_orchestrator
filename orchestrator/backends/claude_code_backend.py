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
import subprocess
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


# Mode-B specific submit instructions appended after the agent's own prompt.
# IMPORTANT: Do NOT use tool-calling language here — Mode B outputs XML, not tool calls.
SUBMIT_INSTRUCTIONS: dict[str, str] = {
    "pm": """
---
IMPORTANT: Do NOT call any tools. Instead, output your final result as plain text ending with
a <submit> block containing valid JSON:

<submit>
{
  "tasks": [
    {"id": "T1", "title": "...", "description": "...", "priority": 1, "status": "pending"}
  ]
}
</submit>""",

    "analyser": """
---
IMPORTANT: Do NOT call any tools. Instead, output your full technical spec as plain text
ending with a <submit> block containing valid JSON. All arrays must be present (use [] if empty):

<submit>
{
  "overview": "...",
  "components": [{"name": "...", "responsibility": "...", "dependencies": []}],
  "api_contracts": [{"method": "GET", "path": "/", "request_schema": {}, "response_schema": {}, "errors": []}],
  "data_models": [],
  "risks": [{"description": "...", "severity": "low", "mitigation": "..."}],
  "acceptance_criteria": ["Given a GET request to /, when the server is running, then return 200 with 'Hello, World!'"]
}
</submit>""",

    "engineer": """
---
IMPORTANT: Write all required files using your file tools. Then output a <submit> block:

<submit>
{
  "artifact_paths": {"filename.py": "./artifacts/filename.py"},
  "summary": "Brief description of what was implemented"
}
</submit>""",

    "qa": """
---
IMPORTANT: Run tests using your tools. Then output your TestReport as a <submit> block:

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


async def _run_subprocess(
    cmd: list[str],
    env: dict[str, str],
    cwd: str | None,
    stdin_data: bytes | None = None,
) -> tuple[bytes, bytes, int]:
    """
    Windows-safe subprocess runner.

    Two Windows limitations addressed here:
    1. asyncio.create_subprocess_exec requires ProactorEventLoop — use thread executor.
    2. Windows cmd.exe command lines cannot contain literal newlines in arguments —
       pass the prompt via stdin instead of as a positional argument.
    """
    loop = asyncio.get_event_loop()
    _proc: list[subprocess.Popen | None] = [None]

    def _blocking() -> tuple[bytes, bytes]:
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=cwd,
        )
        _proc[0] = p
        return p.communicate(input=stdin_data)

    fut: asyncio.Future = loop.run_in_executor(None, _blocking)
    try:
        stdout_bytes, stderr_bytes = await fut
        proc = _proc[0]
        return stdout_bytes, stderr_bytes, proc.returncode if proc else -1
    except asyncio.CancelledError:
        proc = _proc[0]
        if proc:
            proc.kill()
            proc.wait()
        fut.cancel()
        raise


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

        # Build user-turn prompt: agent context + mode-B submit instructions.
        # System prompt is passed via --system-prompt flag to override CLAUDE.md.
        prompt = agent.build_prompt(state) + SUBMIT_INSTRUCTIONS[agent_name]

        # Engineer and QA need filesystem access — run from ARTIFACT_DIR
        artifact_dir = _get_artifact_dir()
        cwd = artifact_dir if agent_name in ("engineer", "qa") else None
        if cwd:
            os.makedirs(cwd, exist_ok=True)

        logger.info("[%s] spawning claude subprocess (model=%s)", agent_name, model)
        start = datetime.now(timezone.utc)

        # Windows cmd.exe cannot handle newlines in CLI arguments.
        # Flatten the system prompt to a single line for --system-prompt flag.
        # The full user prompt is piped via stdin to bypass the argument length limit.
        system_prompt_oneline = " ".join(agent.system_prompt.split())

        # PM and Analyser: disable all tools — they only need to output text.
        # Engineer and QA: allow file system tools for reading/writing artifacts.
        if agent_name in ("engineer", "qa"):
            extra_flags = ["--dangerously-skip-permissions"]
        else:
            extra_flags = ["--tools", ""]   # disable all tools: text output only

        cmd = [
            _claude_cmd(),
            "--model", model,
            "--system-prompt", system_prompt_oneline,  # overrides project CLAUDE.md
            *extra_flags,
            "--output-format", "json",
            "-p",                                      # print mode; reads prompt from stdin
        ]

        # Strip vars that must not leak to the claude subprocess:
        # - CLAUDECODE: blocks nested sessions
        # - Secrets: DATABASE_URL, API keys should never reach the CLI process
        _STRIP = {"CLAUDECODE", "DATABASE_URL", "ANTHROPIC_API_KEY",
                  "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"}
        env = {k: v for k, v in os.environ.items() if k not in _STRIP}

        stdin_data = prompt.encode("utf-8")
        stdout_bytes, stderr_bytes, returncode = await _run_subprocess(
            cmd, env=env, cwd=cwd, stdin_data=stdin_data
        )
        duration = (datetime.now(timezone.utc) - start).total_seconds()

        if returncode != 0:
            err    = stderr_bytes.decode(errors="replace").strip()
            out    = stdout_bytes.decode(errors="replace").strip()
            detail = err or out or "(no output)"
            raise RuntimeError(
                f"[{agent_name}] claude subprocess exited {returncode}:\n{detail}"
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
