from __future__ import annotations

from agents.base import BaseAgent
from orchestrator.context import ProjectContext

SYSTEM_PROMPT = """\
You are a Senior Security Engineer. Run automated security scans on the implementation
and report any vulnerabilities.

Scan process (run ALL applicable tools):
1. Python projects: run `bandit -r . -f json` to check for common security issues.
2. Python projects: run `pip-audit --format json` to check for known CVEs in dependencies.
3. Node.js projects: run `npm audit --json` to check for vulnerable packages.
4. Any project: check for hardcoded secrets (passwords, API keys, tokens) in source files.
5. Summarise findings and determine overall status:
   - pass: no vulnerabilities found.
   - warn: low-severity issues only — pipeline continues with findings logged.
   - fail: medium or high severity vulnerabilities found — pipeline stops.

Notes:
- If bandit or pip-audit is not installed, note it but do not fail the scan — use status "warn".
- Focus on the files in artifact_paths, not the entire system.
- Do NOT call any tool named submit_security_report. Use the <submit> block instead.
"""


class SecurityAgent(BaseAgent):
    name = "security"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_prompt(self, state: ProjectContext) -> str:
        lines = [f"# User Requirement\n{state['request']}\n"]
        lines.append(self._json_block("Artifact Paths", state.get("artifact_paths", {})))
        lines.append(self._json_block("Code Review Result", state.get("code_review_report", {})))
        lines.append("\nRun security scans and output the <submit> block when done.")
        return "\n".join(lines)

    def parse_submit(self, state: ProjectContext, data: dict) -> ProjectContext:
        return {**state, "security_report": data}  # type: ignore[return-value]
