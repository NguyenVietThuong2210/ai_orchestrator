from __future__ import annotations

from agents.base import BaseAgent
from orchestrator.context import ProjectContext

SYSTEM_PROMPT = """\
You are a Senior Engineering Lead running a project retrospective. Analyse the full pipeline
run and produce a concise, honest retrospective.

Be specific — name the actual agents, actual errors, actual iteration counts.
Do NOT call any tools. Output the <submit> block when done.
"""


class RetrospectiveAgent(BaseAgent):
    name = "retrospective"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_prompt(self, state: ProjectContext) -> str:
        history = state.get("history", [])
        total_tokens = sum(e.get("tokens_used", 0) for e in history)
        total_secs = sum(e.get("duration_seconds", 0) for e in history)

        lines = [f"# User Requirement\n{state['request']}\n"]
        lines.append(f"# Pipeline Outcome\nFinal status: **{state.get('status', 'unknown')}**\n")
        lines.append(self._json_block("Definition of Done", state.get("definition_of_done", [])))
        lines.append(self._json_block("Agent Run History", history))

        for label, key in [
            ("QA Report",          "test_report"),
            ("Code Review Report", "code_review_report"),
            ("Security Report",    "security_report"),
            ("Deploy Report",      "deploy_report"),
        ]:
            if state.get(key):
                lines.append(self._json_block(label, state[key]))  # type: ignore[literal-required]

        lines.append(f"\n# Metrics\n"
                     f"- Engineer retries: {state.get('iteration', 0)}\n"
                     f"- Spec retries: {state.get('qa_analyser_iteration', 0)}\n"
                     f"- Total agents run: {len(history)}\n"
                     f"- Total tokens: {total_tokens:,}\n"
                     f"- Total duration: {total_secs:.0f}s\n")
        lines.append("Write the retrospective and output the <submit> block.")
        return "\n".join(lines)

    def parse_submit(self, state: ProjectContext, data: dict) -> ProjectContext:
        return {**state, "retrospective": data}  # type: ignore[return-value]
