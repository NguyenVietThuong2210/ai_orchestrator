"""Analyser Agent — adaptive: full SDD plan for feature, direct answer for query/test/review."""
from __future__ import annotations

import json

from agents.base import BaseAgent
from orchestrator.context import ProjectContext

SYSTEM_PROMPT = """\
You are a Senior Technical Analyst. Your behaviour adapts to the pipeline intent.

## Modes

### Mode: feature (SDD Speckit — plan + clarify commands)

Execute the `plan` and `clarify` speckit commands:

**speckit: clarify** — Before planning, identify open questions from the spec:
- List any gaps in FR/NFR from spec.md that would force implementation guesses
- For each gap, state the default assumption you'll use if not clarified
- Record these as spec clarifications in your output

**speckit: plan** — Produce `plan.md`:
```markdown
# Implementation Plan: {feature name}

## Architecture Decision
[Single paragraph: chosen pattern, why, trade-offs]

## Component Breakdown
| Component | Responsibility | Technology |
|-----------|---------------|------------|
| ...       | ...           | ...        |

## API Design
[Detailed endpoint contracts: method, path, request/response schemas, error codes]

## Data Model
[Table/model definitions with field types, constraints, indexes]

## Sequence Diagrams (text)
[Key flows as numbered steps]

## Risk Register
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|

## Rollout Strategy
[Feature flags, migration plan, backwards compatibility]
```

Also produce a structured `TechnicalSpec` JSON for the graph state.

### Mode: query
Answer the question directly and completely. Be specific, cite file paths and line numbers
where relevant. Call submit_spec with just `query_answer` populated.

### Mode: test
Produce a test plan: which components to test, test types (unit/integration/e2e),
test data requirements, expected outcomes. Call submit_spec with `test_plan`.

### Mode: review
Produce a review checklist: code quality, security, spec compliance, performance.
Call submit_spec with `review_checklist`.

### Mode: bug_fix
Analyse the bug report, identify root cause, propose minimal fix.
Produce tasks for Engineer. Call submit_spec with tasks and `bug_analysis`.

## Rules
- Drain user_message_queue messages targeted at "analyser" or "any".
- For feature mode: spec is the contract — Engineer and QA will depend on it exactly.
- Every acceptance criterion must be testable (Given/When/Then format).
- You MUST call submit_spec exactly once.
"""


class AnalyserAgent(BaseAgent):
    name = "analyser"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_prompt(self, state: ProjectContext) -> str:
        intent = state.get("pipeline_intent", "feature")
        lines = [f"# Pipeline Intent: {intent}\n"]
        lines.append(f"# User Requirement\n{state['request']}\n")

        if state.get("constitution"):
            lines.append(f"# Project Constitution\n{state['constitution']}\n")

        if state.get("spec_md"):
            lines.append(f"# Spec (from PM speckit:specify)\n{state['spec_md']}\n")

        lines.append(self._json_block("Task List", state.get("tasks", [])))

        if state.get("definition_of_done"):
            lines.append(self._json_block("Definition of Done", state["definition_of_done"]))

        # Re-analysis after QA fail-major
        if state.get("test_report") and state["test_report"].get("status") == "fail-major":
            lines.append(self._json_block(
                "Previous QA Report — SPEC WAS WRONG, revise it",
                state["test_report"],
            ))

        # Include prior spec analysis for revision
        if state.get("spec_analysis"):
            lines.append(self._json_block("Spec Analysis Findings to Address", state["spec_analysis"]))

        # Drain queued messages
        queue = state.get("user_message_queue", [])
        relevant = [m for m in queue if m.get("target_agent") in ("analyser", "any")]
        if relevant:
            lines.append("# User Instructions / Additional Context\n")
            for msg in relevant:
                lines.append(f"- {msg['from_user']}\n")

        if intent == "feature":
            lines.append(
                "Execute speckit:clarify then speckit:plan. "
                "Produce plan.md and structured TechnicalSpec. Call submit_spec."
            )
        elif intent == "query":
            lines.append("Answer the question directly. Call submit_spec with query_answer.")
        elif intent == "test":
            lines.append("Produce a test plan. Call submit_spec with test_plan.")
        elif intent == "review":
            lines.append("Produce a review checklist. Call submit_spec with review_checklist.")
        elif intent == "bug_fix":
            lines.append("Analyse the bug, identify root cause, propose fix. Call submit_spec.")

        return "\n".join(lines)

    def parse_submit(self, state: ProjectContext, data: dict) -> ProjectContext:
        # Drain analyser-addressed messages
        queue = state.get("user_message_queue", [])
        remaining = [m for m in queue if m.get("target_agent") not in ("analyser", "any")]

        revision_count = state.get("spec_revision_count", 0)
        if state.get("spec") and data.get("spec"):
            revision_count += 1

        update: dict = {
            "spec_md":              data.get("spec_md", state.get("spec_md", "")),
            "plan_md":              data.get("plan_md", state.get("plan_md", "")),
            "user_message_queue":   remaining,
            "spec_revision_count":  revision_count,
        }

        # Structured spec (TechnicalSpec TypedDict)
        if data.get("spec"):
            update["spec"] = data["spec"]
        elif data.get("overview"):
            # Analyser returned spec fields at top level
            update["spec"] = {
                "overview":            data.get("overview", ""),
                "components":          data.get("components", []),
                "api_contracts":       data.get("api_contracts", []),
                "data_models":         data.get("data_models", []),
                "risks":               data.get("risks", []),
                "acceptance_criteria": data.get("acceptance_criteria", []),
            }

        return {**state, **update}  # type: ignore[return-value]

    @property
    def tools(self) -> list[dict]:
        spec_schema = {
            "type": "object",
            "properties": {
                "overview":            {"type": "string"},
                "components":          {"type": "array", "items": {"type": "object"}},
                "api_contracts":       {"type": "array", "items": {"type": "object"}},
                "data_models":         {"type": "array", "items": {"type": "object"}},
                "risks":               {"type": "array", "items": {"type": "object"}},
                "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
            },
        }
        return [
            {
                "name": "submit_spec",
                "description": "Submit the analyser output (adaptive by intent).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "spec":              spec_schema,
                        "plan_md":           {"type": "string", "description": "specs/plan.md content"},
                        "spec_clarifications": {"type": "array", "items": {"type": "string"},
                                               "description": "Open questions clarified with defaults"},
                        "query_answer":      {"type": "string"},
                        "test_plan":         {"type": "string"},
                        "review_checklist":  {"type": "string"},
                        "bug_analysis":      {"type": "string"},
                    },
                },
            }
        ]
