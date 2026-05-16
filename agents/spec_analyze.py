"""SpecAnalyze agent — five-pass cross-artifact validation (SDD Speckit: analyze command)."""
from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from orchestrator.context import ProjectContext, SpecAnalysisReport, SpecAnalysisFinding


class SpecAnalyzeAgent(BaseAgent):
    name = "spec_analyze"

    @property
    def system_prompt(self) -> str:
        return """\
You are a senior spec validator executing the SDD Speckit `analyze` command.

Your job is to perform a **five-pass cross-artifact analysis** across the constitution,
spec.md, and plan.md documents, identifying issues that would cause implementation failures.

## Five Passes

### Pass 1 — Duplication
Find overlapping or contradictory definitions across artifacts:
- Same endpoint defined twice with different schemas
- Same data field with different types
- Same business rule stated differently

### Pass 2 — Ambiguity
Find statements that are too vague to implement:
- "handle errors appropriately" with no error codes
- "fast response" with no latency SLA
- "secure authentication" with no mechanism specified

### Pass 3 — Under-specification
Find gaps where implementation decisions would be left to the engineer:
- Missing pagination strategy for list endpoints
- No rate limiting policy
- Unspecified database indexing for query-heavy fields

### Pass 4 — Constitution Alignment
Verify every spec decision respects the project's immutable principles:
- Technology stack constraints
- Security requirements (auth, encryption)
- Architecture patterns (sync vs async, monolith vs micro)
- Naming and style conventions

### Pass 5 — Coverage Gaps
Verify the spec covers all user requirements from the original request:
- Every functional requirement has at least one acceptance criterion
- Every acceptance criterion maps to at least one task
- Non-functional requirements (performance, security, availability) are addressed

## Severity Levels
- **CRITICAL**: Will cause build failure or fundamentally wrong implementation
- **HIGH**: Significant rework risk; engineer will make wrong assumption
- **MEDIUM**: Minor ambiguity; can be resolved with reasonable defaults
- **LOW**: Style/clarity improvement; won't block implementation

## Output Format
Call submit_analysis with a JSON object:
```json
{
  "findings": [
    {
      "pass_name": "ambiguity",
      "severity": "HIGH",
      "location": "spec.md §3 Authentication",
      "description": "Token expiry not specified",
      "suggestion": "Add: access_token TTL=15min, refresh_token TTL=7days"
    }
  ],
  "summary": "3 CRITICAL, 2 HIGH, 1 MEDIUM findings. Spec requires revision before implementation.",
  "approved": false
}
```

`approved` must be `true` ONLY if there are zero CRITICAL and zero HIGH findings.
"""

    def build_prompt(self, state: ProjectContext) -> str:
        parts = ["# Spec Analysis Request\n"]

        parts.append(f"**Original request**: {state['request']}\n")

        constitution = state.get("constitution", "")
        if constitution:
            parts.append(f"\n## Constitution\n{constitution}\n")

        spec_md = state.get("spec_md", "")
        if spec_md:
            parts.append(f"\n## spec.md\n{spec_md}\n")

        plan_md = state.get("plan_md", "")
        if plan_md:
            parts.append(f"\n## plan.md\n{plan_md}\n")

        # Include structured spec if available
        if state.get("spec"):
            parts.append(self._json_block("Structured TechnicalSpec", state["spec"]))

        # Include any previous analysis for re-analysis after revision
        revision_count = state.get("spec_revision_count", 0)
        if revision_count > 0:
            parts.append(f"\n**This is revision #{revision_count}** — re-analyze after user/agent revisions.\n")

        if state.get("spec_analysis"):
            parts.append(self._json_block("Previous Analysis", state["spec_analysis"]))

        parts.append("\nPerform all five passes and call submit_analysis with your findings.")
        return "\n".join(parts)

    def parse_submit(self, state: ProjectContext, data: dict) -> ProjectContext:
        findings_raw: list[dict] = data.get("findings", [])
        findings: list[SpecAnalysisFinding] = [
            {
                "pass_name":   f.get("pass_name", ""),
                "severity":    f.get("severity", "LOW"),
                "location":    f.get("location", ""),
                "description": f.get("description", ""),
                "suggestion":  f.get("suggestion", ""),
            }
            for f in findings_raw
        ]
        # Server-side approval validation: approved only if no CRITICAL/HIGH findings.
        # Never trust the agent's own approved field — it may hallucinate.
        blocking = {"CRITICAL", "HIGH"}
        has_blocker = any(f["severity"] in blocking for f in findings)
        approved = (not has_blocker) and bool(data.get("approved", False))

        report: SpecAnalysisReport = {
            "findings": findings,
            "summary":  data.get("summary", ""),
            "approved": approved,
        }
        return {**state, "spec_analysis": report}

    # ── Tool definition (Mode A Anthropic SDK) ────────────────────────────────

    @property
    def tools(self) -> list[dict]:
        return [
            {
                "name": "submit_analysis",
                "description": "Submit the five-pass spec analysis report.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "findings": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "pass_name":   {"type": "string", "enum": ["duplication", "ambiguity", "underspecification", "constitution", "coverage"]},
                                    "severity":    {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
                                    "location":    {"type": "string"},
                                    "description": {"type": "string"},
                                    "suggestion":  {"type": "string"},
                                },
                                "required": ["pass_name", "severity", "location", "description", "suggestion"],
                            },
                        },
                        "summary":  {"type": "string"},
                        "approved": {"type": "boolean"},
                    },
                    "required": ["findings", "summary", "approved"],
                },
            }
        ]
