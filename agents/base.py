"""BaseAgent — shared interface for all four agents."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod

from orchestrator.context import ProjectContext


class BaseAgent(ABC):
    name: str  # "pm" | "analyser" | "engineer" | "qa"

    # ── Subclasses must define ────────────────────────────────────────────────

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt — cached with cache_control in Mode A."""
        ...

    @abstractmethod
    def build_prompt(self, state: ProjectContext) -> str:
        """Build the user-turn prompt from current pipeline state."""
        ...

    @abstractmethod
    def parse_submit(self, state: ProjectContext, data: dict) -> ProjectContext:
        """
        Merge submit tool result into state.
        Called by both Mode A (formal tool call) and Mode B (<submit> block parsed as dict).
        """
        ...

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _json_block(self, label: str, obj: object) -> str:
        return f"# {label}\n```json\n{json.dumps(obj, indent=2, ensure_ascii=False)}\n```\n"
