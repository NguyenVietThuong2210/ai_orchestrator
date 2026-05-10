from __future__ import annotations

import json
import os

from agents.base import BaseAgent
from orchestrator.context import ProjectContext


def _artifact_dir() -> str:
    return os.getenv("ARTIFACT_DIR", "./artifacts")


_SYSTEM_PROMPT_TEMPLATE = """\
You are a Senior Software Engineer. Implement the feature exactly as described in the technical spec.

Rules:
- Write production-quality code, no placeholders, no TODOs.
- All files go to: {artifact_dir}/
- Include a requirements.txt or pyproject.toml if installing packages.
- If fixing QA defects, address every defect in the report — do not skip any.
- You MUST call submit_implementation exactly once when all files are written.
"""


class EngineerAgent(BaseAgent):
    name = "engineer"

    @property
    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT_TEMPLATE.format(artifact_dir=_artifact_dir())

    def build_prompt(self, state: ProjectContext) -> str:
        artifact_dir = _artifact_dir()
        lines = [f"# User Requirement\n{state['request']}\n"]
        lines.append(self._json_block("Technical Spec", state.get("spec", {})))
        lines.append(self._json_block("Task List", state.get("tasks", [])))

        report = state.get("test_report")
        if report and report["status"] in ("fail-minor", "fail-major"):
            iteration = state.get("iteration", 0)
            lines.append(
                f"\n# QA Defect Report (iteration {iteration} — fix ALL defects below)\n"
            )
            lines.append(self._json_block("Defects", report.get("defects", [])))

        lines.append(
            f"\nWrite all implementation files to {artifact_dir}/ "
            "then call submit_implementation."
        )
        return "\n".join(lines)

    def parse_submit(self, state: ProjectContext, data: dict) -> ProjectContext:
        return {**state, "artifact_paths": data["artifact_paths"]}  # type: ignore[return-value]
