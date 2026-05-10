"""Backend factory — selects Mode A or Mode B based on AI_BACKEND env var."""
from __future__ import annotations

import os

from orchestrator.backends.base import BaseBackend


def get_backend() -> BaseBackend:
    """
    Returns the active backend singleton based on AI_BACKEND env var.

    AI_BACKEND=claude_code  → ClaudeCodeBackend (Mode B, default)
    AI_BACKEND=api          → AnthropicAPIBackend (Mode A)
    """
    mode = os.getenv("AI_BACKEND", "claude_code").lower()

    if mode == "api":
        from orchestrator.backends.api_backend import AnthropicAPIBackend
        return AnthropicAPIBackend()

    if mode == "claude_code":
        from orchestrator.backends.claude_code_backend import ClaudeCodeBackend
        return ClaudeCodeBackend()

    raise ValueError(
        f"Unknown AI_BACKEND='{mode}'. Valid values: 'claude_code' | 'api'"
    )
