from __future__ import annotations

import json

from agents.base import BaseAgent
from orchestrator.context import ProjectContext

SYSTEM_PROMPT = """\
You are a Senior Technical Analyst. Given a task list, produce a complete technical specification
following SDD (Specification-Driven Development) format.

The spec is the single source of truth. Engineer codes from it. QA validates against it.

Spec must include:
- overview: one-paragraph system description
- components: list of {name, responsibility, dependencies}
- api_contracts: list of {method, path, request_schema, response_schema, errors}
- data_models: list of {name, fields: [{name, type, constraints}]}
- risks: list of {description, severity, mitigation}
- acceptance_criteria: list of testable strings ("Given X, when Y, then Z")

You MUST call submit_spec exactly once when the spec is complete.
"""


class AnalyserAgent(BaseAgent):
    name = "analyser"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_prompt(self, state: ProjectContext) -> str:
        lines = [f"# User Requirement\n{state['request']}\n"]
        lines.append(self._json_block("Task List", state.get("tasks", [])))

        if state.get("test_report") and state["test_report"]["status"] == "fail-major":
            lines.append(self._json_block("Previous QA Report — Spec was wrong, fix it",
                                          state["test_report"]))

        lines.append("Produce the full technical spec and call submit_spec when complete.")
        return "\n".join(lines)

    def parse_submit(self, state: ProjectContext, data: dict) -> ProjectContext:
        return {**state, "spec": data}  # type: ignore[return-value]
