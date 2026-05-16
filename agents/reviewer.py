from __future__ import annotations

from agents.base import BaseAgent
from orchestrator.context import ProjectContext

SYSTEM_PROMPT = """\
You are a Senior Code Reviewer. Review the engineer's implementation against the technical spec
and the project's Definition of Done.

Review process:
1. Read the Technical Spec — understand what was supposed to be built.
2. Read the Definition of Done — these are the mandatory pass criteria.
3. Read the artifact_paths — understand which files were created.
4. Check the implementation for:
   - Correctness: does the code match the spec's acceptance criteria?
   - Completeness: are all required files present?
   - Code quality: obvious bugs, missing error handling, hardcoded values that should be config.
   - DoD compliance: does each DoD item appear satisfied based on the code structure?
5. Classify issues:
   - minor: style, naming, missing edge case — can be fixed quickly.
   - major: wrong logic, missing component, spec misunderstood.
6. Determine status:
   - pass: no blocking issues — proceed to security scan.
   - fail: has major issues, or ≥3 minor issues — send back to Engineer.

Do NOT call any tools. Output the <submit> block when done.
"""


class CodeReviewerAgent(BaseAgent):
    name = "reviewer"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_prompt(self, state: ProjectContext) -> str:
        lines = [f"# User Requirement\n{state['request']}\n"]
        lines.append(self._json_block("Technical Spec", state.get("spec", {})))
        lines.append(self._json_block("Definition of Done", state.get("definition_of_done", [])))
        lines.append(self._json_block("Artifact Paths (files written by Engineer)", state.get("artifact_paths", {})))
        iteration = state.get("iteration", 0)
        if iteration > 0:
            lines.append(f"\n> This is review iteration #{iteration}. Check that previous issues were resolved.\n")
        lines.append("Review the implementation and output the <submit> block.")
        return "\n".join(lines)

    def parse_submit(self, state: ProjectContext, data: dict) -> ProjectContext:
        return {**state, "code_review_report": data}  # type: ignore[return-value]
