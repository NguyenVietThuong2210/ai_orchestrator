"""
Mode A backend — Anthropic API direct calls.

Requires ANTHROPIC_API_KEY. Runs fully automated, no session needed.
Placeholder for now — implement when API key is available.
"""
from __future__ import annotations

import os

from orchestrator.backends.base import BaseBackend
from orchestrator.context import ProjectContext

# Per-agent models for Mode A
DEFAULT_MODELS_A: dict[str, str] = {
    "pm":       os.getenv("PM_MODEL",       "claude-haiku-4-5-20251001"),
    "analyser": os.getenv("ANALYSER_MODEL", "claude-opus-4-7"),
    "engineer": os.getenv("ENGINEER_MODEL", "claude-sonnet-4-6"),
    "qa":       os.getenv("QA_MODEL",       "claude-sonnet-4-6"),
}


class AnthropicAPIBackend(BaseBackend):
    """Direct Anthropic API calls with prompt caching. Requires ANTHROPIC_API_KEY."""

    async def run(self, agent_name: str, state: ProjectContext) -> ProjectContext:
        # TODO: implement when API key is available
        # Pattern: agentic loop until submit tool is called
        # Uses same _build_prompt() and _parse_submit() logic as ClaudeCodeBackend
        raise NotImplementedError(
            "Mode A not implemented yet. Set AI_BACKEND=claude_code to use Mode B."
        )
