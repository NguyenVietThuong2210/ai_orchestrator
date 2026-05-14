from __future__ import annotations

from agents.base import BaseAgent
from orchestrator.context import ProjectContext

SYSTEM_PROMPT = """\
You are a Senior QA Engineer. Validate the implementation against the technical spec.

Validation process:
1. Read every file listed in artifact_paths.
2. Check each acceptance criterion in the spec.
3. Run available tests (pytest, npm test, etc.) using run_shell.
4. Classify defects:
   - minor: wrong logic, missing edge case, style — Engineer can fix.
   - major: spec misunderstood, wrong architecture, missing component — Analyser must fix spec.
5. Determine status:
   - pass:       all acceptance criteria met, no blocking defects.
   - fail-minor: fixable defects only — Engineer retry.
   - fail-major: spec was wrong — Analyser retry.

After validation, output a <submit> block as instructed — do NOT call any tool named submit_test_report.
"""


class QAAgent(BaseAgent):
    name = "qa"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_prompt(self, state: ProjectContext) -> str:
        lines = [f"# User Requirement\n{state['request']}\n"]
        lines.append(self._json_block("Technical Spec", state.get("spec", {})))
        lines.append(self._json_block("Artifact Paths", state.get("artifact_paths", {})))

        iteration = state.get("iteration", 0)
        qa_iter   = state.get("qa_analyser_iteration", 0)
        if iteration > 0 or qa_iter > 0:
            lines.append(
                f"\n> This is retry #{iteration} (engineer) / #{qa_iter} (analyser). "
                "Be thorough — check defects from previous report are resolved.\n"
            )

        lines.append("Validate the implementation and output the <submit> block when done.")
        return "\n".join(lines)

    def parse_submit(self, state: ProjectContext, data: dict) -> ProjectContext:
        updated = dict(state)
        updated["test_report"] = data

        if data["status"] == "fail-minor":
            updated["iteration"] = state.get("iteration", 0) + 1
        elif data["status"] == "fail-major":
            updated["qa_analyser_iteration"] = state.get("qa_analyser_iteration", 0) + 1

        return updated  # type: ignore[return-value]
