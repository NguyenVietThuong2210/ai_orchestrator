"""
Mode B backend — Claude Code sub-agents via `claude` CLI.

No ANTHROPIC_API_KEY needed: uses Pro subscription auth from the active Claude Code session.
Requires `claude` CLI installed and an active Claude Code session when the pipeline runs.

How it works:
  1. Each agent turn spawns `claude -p <prompt> --model <model>` as a subprocess
  2. The prompt = agent.build_prompt(state) + SUBMIT_INSTRUCTIONS (mode-B specific)
  3. We parse the <submit>...</submit> block and call agent.parse_submit(state, data)
  4. Engineer / QA / Security / Deploy run with cwd=project_dir so file tools work naturally
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

MAX_AGENT_RETRIES = 1  # transient failures: 1 retry = 2 total attempts

# Token costs per 1K tokens (USD) — published pricing as of 2025-05.
# Update here when Anthropic changes rates.
_MODEL_COST_PER_1K_INPUT_TOKENS: dict[str, float] = {
    "claude-opus-4-7":           0.015,    # $15 / M input
    "claude-sonnet-4-6":         0.003,    # $3 / M input
    "claude-haiku-4-5-20251001": 0.0008,   # $0.80 / M input
}
_MODEL_COST_PER_1K_OUTPUT_TOKENS: dict[str, float] = {
    "claude-opus-4-7":           0.075,    # $75 / M output
    "claude-sonnet-4-6":         0.015,    # $15 / M output
    "claude-haiku-4-5-20251001": 0.00125,  # $1.25 / M output
}

# Agents that need filesystem/shell access → --dangerously-skip-permissions + project_dir cwd
_SHELL_AGENTS = {"engineer", "qa", "security", "deploy"}

# Agents that only output text → --tools "" (disables all tools)
_TEXT_ONLY_AGENTS = {"pm", "analyser", "reviewer", "retrospective", "spec_analyze", "task_decompose"}


def _get_project_cwd(state) -> str:
    """Return the project root directory for shell-capable agent subprocess cwd."""
    project_dir = state.get("project_dir") if state else None
    if project_dir:
        return project_dir
    return os.getenv("PROJECTS_ROOT", "./projects")


def _claude_cmd() -> str:
    """Return 'claude.cmd' on Windows (asyncio.create_subprocess_exec can't resolve .cmd
    via PATHEXT), plain 'claude' elsewhere."""
    return "claude.cmd" if os.name == "nt" else "claude"


def _get_model(agent_name: str) -> str:
    """Lazy model lookup — reads ENV at call time, after load_dotenv()."""
    defaults = {
        "pm":             "claude-haiku-4-5-20251001",
        "analyser":       "claude-sonnet-4-6",
        "engineer":       "claude-sonnet-4-6",
        "qa":             "claude-sonnet-4-6",
        "reviewer":       "claude-haiku-4-5-20251001",
        "security":       "claude-sonnet-4-6",
        "deploy":         "claude-sonnet-4-6",
        "retrospective":  "claude-haiku-4-5-20251001",
        "spec_analyze":   "claude-sonnet-4-6",
        "task_decompose": "claude-haiku-4-5-20251001",
    }
    return os.getenv(f"{agent_name.upper()}_MODEL_B", defaults.get(agent_name, "claude-sonnet-4-6"))


# Mode-B specific submit instructions appended after the agent's own prompt.
# IMPORTANT: Do NOT use tool-calling language here — Mode B outputs XML, not tool calls.
SUBMIT_INSTRUCTIONS: dict[str, str] = {
    "pm": """
---
IMPORTANT: Do NOT call any tools. Output your final result as plain text ending with
a <submit> block containing valid JSON:

<submit>
{
  "tasks": [
    {"id": "T1", "title": "...", "description": "...", "priority": 1, "status": "pending"}
  ],
  "definition_of_done": [
    "GET / returns HTTP 200 with body 'Hello, World!'",
    "python manage.py check exits with 0 errors"
  ],
  "needs_clarification": false,
  "clarification_questions": []
}
</submit>""",

    "analyser": """
---
IMPORTANT: Do NOT call any tools. Output your full technical spec as plain text
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
IMPORTANT: Write all required files using your file tools directly in the current directory \
(the project root — do NOT create an 'artifacts/' or 'projects/' subdirectory). \
The spec/ subdirectory in this folder is for documentation — do NOT write code files there. \
Then output a <submit> block. Paths in artifact_paths are relative to the current directory:

<submit>
{
  "artifact_paths": {"manage.py": "manage.py", "config/settings.py": "config/settings.py"},
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

    "reviewer": """
---
IMPORTANT: Do NOT call any tools — review based on the spec and artifact paths provided.
Output your code review as a <submit> block:

<submit>
{
  "status": "pass",
  "issues": [
    {"file": "views.py", "line": 10, "severity": "minor", "description": "Missing docstring"}
  ],
  "summary": "Implementation matches spec. No blocking issues found."
}
</submit>
Valid status values: "pass" | "fail"
""",

    "security": """
---
IMPORTANT: Run security scans using your shell tools. Then output a <submit> block:

<submit>
{
  "status": "pass",
  "vulnerabilities": [
    {"tool": "bandit", "id": "B105", "severity": "low", "description": "Hardcoded password", "file": "settings.py"}
  ],
  "summary": "No critical vulnerabilities found."
}
</submit>
Valid status values: "pass" | "warn" | "fail"
""",

    "deploy": """
---
IMPORTANT: Use your shell tools to install dependencies, start the app, and run a smoke test.
Then output a <submit> block:

<submit>
{
  "status": "pass",
  "endpoint": "http://localhost:9000/",
  "response": "200 OK — body: Hello, World!",
  "command_used": "python manage.py runserver 0.0.0.0:9000"
}
</submit>
Valid status values: "pass" | "fail"
""",

    "retrospective": """
---
IMPORTANT: Do NOT call any tools. Output your retrospective as a <submit> block:

<submit>
{
  "what_worked": ["PM produced clear tasks", "Analyser spec was accurate"],
  "what_failed": ["Engineer needed 2 retries due to missing URL config"],
  "lessons": ["Spec should explicitly list all URL patterns"],
  "metrics": {
    "total_agents": 7,
    "total_tokens": 12500,
    "qa_retries": 1,
    "spec_retries": 0,
    "duration_seconds": 340
  }
}
</submit>""",
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
    timeout: float | None = None,
) -> tuple[bytes, bytes, int]:
    """
    Windows-safe subprocess runner.

    Two Windows limitations addressed here:
    1. asyncio.create_subprocess_exec requires ProactorEventLoop — use thread executor.
    2. Windows cmd.exe command lines cannot contain literal newlines in arguments —
       pass the prompt via stdin instead of as a positional argument.

    timeout: seconds before the subprocess is killed and asyncio.TimeoutError is raised.
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
        if timeout is not None:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(fut, timeout=timeout)
        else:
            stdout_bytes, stderr_bytes = await fut
        proc = _proc[0]
        return stdout_bytes, stderr_bytes, proc.returncode if proc else -1
    except asyncio.TimeoutError:
        proc = _proc[0]
        if proc:
            proc.kill()
            proc.wait()
        raise
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
    - Tools:  Shell agents (engineer/qa/security/deploy) run with cwd=project_dir
    """

    async def run(self, agent_name: str, state: ProjectContext) -> ProjectContext:
        from agents import AGENTS

        agent  = AGENTS[agent_name]
        model  = _get_model(agent_name)
        timeout = float(os.getenv("AGENT_TIMEOUT_SECONDS", "300"))

        prompt = agent.build_prompt(state) + SUBMIT_INSTRUCTIONS[agent_name]

        cwd = _get_project_cwd(state) if agent_name in _SHELL_AGENTS else None
        if cwd:
            os.makedirs(cwd, exist_ok=True)

        system_prompt_oneline = " ".join(agent.system_prompt.split())

        extra_flags = (
            ["--dangerously-skip-permissions"] if agent_name in _SHELL_AGENTS
            else ["--tools", ""]
        )
        cmd = [
            _claude_cmd(),
            "--model", model,
            "--system-prompt", system_prompt_oneline,
            *extra_flags,
            "--output-format", "json",
            "-p",
        ]

        _STRIP = {"CLAUDECODE", "DATABASE_URL", "ANTHROPIC_API_KEY",
                  "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"}
        env        = {k: v for k, v in os.environ.items() if k not in _STRIP}
        stdin_data = prompt.encode("utf-8")
        start      = datetime.now(timezone.utc)

        logger.info("[%s] spawning claude subprocess (model=%s, timeout=%.0fs)",
                    agent_name, model, timeout)

        # ── Retry loop (transient subprocess/output failures) ──────────────────
        last_exc: Exception | None = None
        text_output = ""
        tokens      = 0
        data: dict  = {}

        for attempt in range(MAX_AGENT_RETRIES + 1):
            if attempt > 0:
                wait = 5 * attempt
                logger.warning("[%s] retry %d/%d in %ds — %s",
                               agent_name, attempt, MAX_AGENT_RETRIES, wait, last_exc)
                await asyncio.sleep(wait)

            try:
                stdout_bytes, stderr_bytes, returncode = await _run_subprocess(
                    cmd, env=env, cwd=cwd, stdin_data=stdin_data, timeout=timeout
                )
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"[{agent_name}] subprocess timed out after {timeout:.0f}s "
                    f"(set AGENT_TIMEOUT_SECONDS env to adjust)"
                )

            if returncode != 0:
                err    = stderr_bytes.decode(errors="replace").strip()
                out    = stdout_bytes.decode(errors="replace").strip()
                detail = err or out or "(no output)"
                last_exc = RuntimeError(
                    f"[{agent_name}] claude subprocess exited {returncode}:\n{detail}"
                )
                continue

            raw = stdout_bytes.decode(errors="replace")
            try:
                envelope      = json.loads(raw)
                text_output   = envelope.get("result", raw)
                usage         = envelope.get("usage", {})
                input_tokens  = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
            except json.JSONDecodeError:
                text_output   = raw
                input_tokens  = 0
                output_tokens = 0

            # Budget guard uses output tokens (the controllable metric).
            # Never retry on budget exceeded — raise immediately.
            max_tokens = int(os.getenv("MAX_TOKENS_PER_AGENT", "0"))
            if max_tokens > 0:
                pct = output_tokens / max_tokens * 100
                if pct >= 80:
                    logger.warning(
                        "[%s] output tokens at %.0f%% of budget (%d / %d)",
                        agent_name, pct, output_tokens, max_tokens,
                    )
                if output_tokens > max_tokens:
                    raise RuntimeError(
                        f"[{agent_name}] token budget exceeded: {output_tokens:,} > {max_tokens:,} "
                        f"(set MAX_TOKENS_PER_AGENT env to raise limit)"
                    )

            try:
                data     = _extract_submit_data(agent_name, text_output)
                last_exc = None
                break  # success
            except ValueError as exc:
                last_exc = exc
                continue

        if last_exc is not None:
            raise last_exc

        duration = (datetime.now(timezone.utc) - start).total_seconds()
        cost_usd = (
            input_tokens  / 1000 * _MODEL_COST_PER_1K_INPUT_TOKENS.get(model, 0.003)
            + output_tokens / 1000 * _MODEL_COST_PER_1K_OUTPUT_TOKENS.get(model, 0.015)
        )
        logger.info("[%s] done in %.1fs, in=%d out=%d cost=$%.4f",
                    agent_name, duration, input_tokens, output_tokens, cost_usd)

        updated = agent.parse_submit(state, data)

        prev_cost: float = state.get("cost_estimate_usd") or 0.0  # type: ignore[assignment]
        event: AgentEvent = {
            "agent":            agent_name,
            "timestamp":        start.isoformat(),
            "status":           "ok",
            "tokens_used":      output_tokens,   # output tokens — budget-relevant metric
            "duration_seconds": duration,
            "note":             f"mode=claude_code model={model} in={input_tokens} out={output_tokens} cost=${cost_usd:.4f}",
        }
        updated["history"]           = list(state.get("history", [])) + [event]
        updated["cost_estimate_usd"] = prev_cost + cost_usd

        return updated
