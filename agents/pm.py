from __future__ import annotations

from agents.base import BaseAgent
from orchestrator.context import ProjectContext

SYSTEM_PROMPT = """\
You are a Senior Product Manager. Analyse the user requirement and break it into a structured,
prioritised task list. Each task must be atomic — one clear deliverable per task.

Rules:
- Priority 1 = must-have for MVP. Priority 5 = nice-to-have.
- Tasks must be ordered so each depends only on prior tasks.
- IDs: T1, T2, T3, …
- You MUST call submit_plan exactly once when your task list is complete.
"""


class PMAgent(BaseAgent):
    name = "pm"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_prompt(self, state: ProjectContext) -> str:
        lines = [f"# User Requirement\n{state['request']}\n"]
        if state.get("test_report"):
            # Re-planning after major QA failure is Analyser's job, not PM's.
            # PM is only called once at the start.
            pass
        lines.append(
            "Produce a structured task list and call submit_plan when complete."
        )
        return "\n".join(lines)

    def parse_submit(self, state: ProjectContext, data: dict) -> ProjectContext:
        return {**state, "tasks": data["tasks"]}  # type: ignore[return-value]
