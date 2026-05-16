"""PM Agent — intent classification, constitution, SDD Speckit specify."""
from __future__ import annotations

from agents.base import BaseAgent
from orchestrator.context import ProjectContext

SYSTEM_PROMPT = """\
You are a Senior Product Manager and SDD Speckit orchestrator.

## Primary Job: Classify Pipeline Intent

Before anything else, classify the user request into exactly one intent:

| Intent   | When to use | Pipeline route |
|----------|-------------|----------------|
| query    | Question about the project, codebase, or a concept | PM → Analyser (answer only) |
| test     | "Run tests", "verify this works", "check coverage" | PM → QA (no dev) |
| bug_fix  | Bug report with reproduction steps | PM → Analyser → Engineer → QA |
| feature  | New capability, endpoint, component, or system | Full SDD Speckit pipeline |
| review   | "Review the code", "audit the spec", "security review" | PM → Analyser → Reviewer |

## For `feature` intent — SDD Speckit Flow

When intent is `feature`, also execute the **specify** command:

### Speckit: specify
Generate a formal `spec.md` using this structure:
```markdown
# Spec: {feature name}

## 1. Problem Statement
What problem does this solve? Who is the user?

## 2. Goals
Bullet list of measurable goals (not vague aspirations)

## 3. Non-Goals
Explicit scope exclusions to prevent scope creep

## 4. Functional Requirements
FR-001: [Actor] can [action] so that [value]
FR-002: ...

## 5. Non-Functional Requirements
NFR-001: P95 response time < 200ms under 100 RPS
NFR-002: Zero PII stored in logs
...

## 6. Open Questions
Questions that must be answered before implementation begins
```

### Speckit: constitution (first run only)
If no constitution exists, also generate `constitution.md` — the project's immutable principles:
```markdown
# Project Constitution

## Technology Stack
- Language: Python 3.11+
- Framework: FastAPI
- Database: PostgreSQL with SQLAlchemy ORM

## Architecture Principles
- Async-first: all I/O must use async/await
- No ORM queries in route handlers (use service layer)

## Security Mandates
- All endpoints require JWT authentication except /health
- Secrets via environment variables only — never hardcoded

## Code Style
- Ruff formatter, 88-char line limit
- Type hints on all public functions
```

## For `query` intent
Answer the question directly in the `query_answer` field. No tasks, no spec.

## Rules
- Classify intent FIRST — wrong intent causes the wrong agents to run.
- Definition of Done items must be measurable ("GET /users returns 200" not "it works").
- If critical info is missing for a feature, set needs_clarification=true.
- You MUST call submit_plan exactly once.

## Draining User Messages
Check user_message_queue. If messages are addressed to "pm" or "any", incorporate them
into your classification and planning before submitting.
"""


class PMAgent(BaseAgent):
    name = "pm"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_prompt(self, state: ProjectContext) -> str:
        lines = [f"# User Requirement\n{state['request']}\n"]

        if state.get("clarification_context"):
            lines.append(f"# Additional Context (from user clarification)\n{state['clarification_context']}\n")

        if state.get("constitution"):
            lines.append(f"# Existing Constitution\n{state['constitution']}\n")

        # Drain queued messages addressed to PM
        queue = state.get("user_message_queue", [])
        relevant = [m for m in queue if m.get("target_agent") in ("pm", "any")]
        if relevant:
            lines.append("# User Instructions\n")
            for msg in relevant:
                lines.append(f"- {msg['from_user']}\n")

        lines.append(
            "1. Classify the pipeline intent.\n"
            "2. If intent is 'feature': produce spec.md, constitution (if missing), tasks, and DoD.\n"
            "3. If intent is 'query': answer directly.\n"
            "4. Call submit_plan when done."
        )
        return "\n".join(lines)

    def parse_submit(self, state: ProjectContext, data: dict) -> ProjectContext:
        # Drain PM-addressed messages from queue
        queue = state.get("user_message_queue", [])
        remaining = [m for m in queue if m.get("target_agent") not in ("pm", "any")]

        return {
            **state,
            "pipeline_intent":         data.get("pipeline_intent", "feature"),
            "tasks":                   data.get("tasks", []),
            "definition_of_done":      data.get("definition_of_done", []),
            "needs_clarification":     data.get("needs_clarification", False),
            "clarification_questions": data.get("clarification_questions", []),
            "constitution":            data.get("constitution", state.get("constitution", "")),
            "spec_md":                 data.get("spec_md", state.get("spec_md", "")),
            "user_message_queue":      remaining,
            # query answers go into history note, not a separate field
        }  # type: ignore[return-value]

    @property
    def tools(self) -> list[dict]:
        return [
            {
                "name": "submit_plan",
                "description": "Submit PM output: intent classification, tasks, spec.md, constitution.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pipeline_intent": {
                            "type": "string",
                            "enum": ["query", "test", "bug_fix", "feature", "review"],
                            "description": "Classified pipeline intent",
                        },
                        "query_answer": {
                            "type": "string",
                            "description": "Direct answer (only for intent=query)",
                        },
                        "tasks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id":          {"type": "string"},
                                    "title":       {"type": "string"},
                                    "description": {"type": "string"},
                                    "priority":    {"type": "integer"},
                                    "status":      {"type": "string"},
                                    "phase":       {"type": "string"},
                                    "depends_on":  {"type": "array", "items": {"type": "string"}},
                                    "parallel":    {"type": "boolean"},
                                },
                                "required": ["id", "title", "description", "priority", "status"],
                            },
                        },
                        "definition_of_done":      {"type": "array", "items": {"type": "string"}},
                        "needs_clarification":     {"type": "boolean"},
                        "clarification_questions": {"type": "array", "items": {"type": "string"}},
                        "constitution": {
                            "type": "string",
                            "description": "specs/constitution.md content (immutable project principles)",
                        },
                        "spec_md": {
                            "type": "string",
                            "description": "specs/spec.md content from speckit specify command",
                        },
                    },
                    "required": ["pipeline_intent", "needs_clarification"],
                },
            }
        ]
