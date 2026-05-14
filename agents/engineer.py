from __future__ import annotations

from agents.base import BaseAgent
from orchestrator.context import ProjectContext


_SYSTEM_PROMPT = """\
You are a Senior Software Engineer. Implement the feature exactly as described in the technical spec.

Rules:
- Write production-quality code, no placeholders, no TODOs.
- Write all files to the CURRENT DIRECTORY using your file tools.
- Do NOT create an "artifacts/" or "projects/" subdirectory — you are already inside the project root.
- The spec/ subdirectory exists for documentation — do NOT write code files there.
- Include a requirements.txt or pyproject.toml if installing packages.
- If fixing QA defects, address every defect in the report — do not skip any.
- After writing all files, output a <submit> block as instructed — do NOT call any tool named submit.
"""


class EngineerAgent(BaseAgent):
    name = "engineer"

    @property
    def system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    def build_prompt(self, state: ProjectContext) -> str:
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
            "\nWrite all files to the current directory (the project root). "
            "Do NOT write into spec/ — that folder is for documentation. "
            "Then output the <submit> block."
        )
        return "\n".join(lines)

    def parse_submit(self, state: ProjectContext, data: dict) -> ProjectContext:
        return {**state, "artifact_paths": data["artifact_paths"]}  # type: ignore[return-value]
