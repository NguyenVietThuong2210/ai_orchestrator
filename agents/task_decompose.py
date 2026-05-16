"""TaskDecompose agent — dependency-ordered task graph (SDD Speckit: tasks command)."""
from __future__ import annotations

from agents.base import BaseAgent
from orchestrator.context import ProjectContext, Task


def _detect_cycle(tasks: list[Task]) -> list[str] | None:
    """DFS cycle detection on the task dependency graph.
    Returns the cycle as a list of task IDs, or None if the graph is acyclic."""
    graph: dict[str, list[str]] = {t["id"]: list(t.get("depends_on") or []) for t in tasks}
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {tid: WHITE for tid in graph}
    path: list[str] = []

    def dfs(node: str) -> list[str] | None:
        color[node] = GRAY
        path.append(node)
        for dep in graph.get(node, []):
            if dep not in graph:
                continue  # dangling reference — ignore (separate validation concern)
            if color[dep] == GRAY:
                idx = path.index(dep)
                return path[idx:]
            if color[dep] == WHITE:
                result = dfs(dep)
                if result:
                    return result
        path.pop()
        color[node] = BLACK
        return None

    for tid in list(graph.keys()):
        if color[tid] == WHITE:
            result = dfs(tid)
            if result:
                return result
    return None


class TaskDecomposeAgent(BaseAgent):
    name = "task_decompose"

    @property
    def system_prompt(self) -> str:
        return """\
You are a senior technical lead executing the SDD Speckit `tasks` command.

Your job is to produce a **dependency-ordered task graph** from the approved spec and plan,
structured in four phases with explicit parallel markers.

## Four Phases

### Phase 1 — Setup
Infrastructure, configuration, project skeleton:
- Dev environment, CI/CD, database migrations
- Package installation, directory structure

### Phase 2 — Foundation
Core data models, shared utilities, auth:
- Database schemas, ORM models
- Authentication/authorization middleware
- Shared error handling, logging, config

### Phase 3 — Stories
User-facing features, business logic, API endpoints:
- Each story maps to one or more acceptance criteria from spec
- Each story must reference its spec section

### Phase 4 — Polish
Tests, documentation, performance, edge cases:
- Unit + integration tests for every story
- API documentation (OpenAPI/Postman)
- Performance optimization, error message polish

## Task Rules
- Each task has a unique ID: `T{phase_number}.{sequence}` (e.g. T1.1, T2.3, T3.12)
- `depends_on`: list of task IDs that must complete before this task starts
- `parallel`: true if this task can run concurrently with its sibling tasks in the same phase
- `priority`: 1 (must-do MVP) → 5 (nice-to-have)
- Tasks within a phase that don't depend on each other SHOULD be marked `parallel: true`

## Output Format
Call submit_tasks with:
```json
{
  "tasks": [
    {
      "id": "T1.1",
      "title": "Initialize FastAPI project",
      "description": "Create project skeleton with pyproject.toml, main.py, folder structure",
      "phase": "Setup",
      "priority": 1,
      "status": "pending",
      "depends_on": [],
      "parallel": false
    },
    {
      "id": "T2.1",
      "title": "Define User model",
      "description": "SQLAlchemy User model with id, email, hashed_password, created_at",
      "phase": "Foundation",
      "priority": 1,
      "status": "pending",
      "depends_on": ["T1.1"],
      "parallel": true
    }
  ],
  "tasks_md": "# Task Graph\\n\\n## Phase 1 — Setup\\n- [P] T1.1 ...",
  "summary": "23 tasks across 4 phases. T3.x stories can be parallelized after T2.x completes."
}
```

`tasks_md` should be a formatted markdown task list suitable for saving to specs/tasks.md.
Mark parallel tasks with `[P]` prefix in the markdown.
"""

    def build_prompt(self, state: ProjectContext) -> str:
        parts = ["# Task Decomposition Request\n"]
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

        if state.get("spec"):
            parts.append(self._json_block("Structured TechnicalSpec", state["spec"]))

        if state.get("definition_of_done"):
            parts.append(self._json_block("Definition of Done", state["definition_of_done"]))

        # Analysis findings guide task priority
        if state.get("spec_analysis"):
            analysis = state["spec_analysis"]
            if analysis.get("findings"):
                parts.append(self._json_block("Spec Analysis Findings (address in tasks)", analysis["findings"]))

        # Drain any queued user messages
        queue = state.get("user_message_queue", [])
        relevant = [m for m in queue if m.get("target_agent") in ("task_decompose", "any")]
        if relevant:
            parts.append("\n## User Instructions for Task Decomposition\n")
            for msg in relevant:
                parts.append(f"- {msg['from_user']}\n")

        parts.append("\nDecompose into a dependency-ordered task graph and call submit_tasks.")
        return "\n".join(parts)

    def parse_submit(self, state: ProjectContext, data: dict) -> ProjectContext:
        raw_tasks: list[dict] = data.get("tasks", [])
        tasks: list[Task] = []
        for t in raw_tasks:
            tasks.append({
                "id":          t.get("id", ""),
                "title":       t.get("title", ""),
                "description": t.get("description", ""),
                "phase":       t.get("phase", "Stories"),
                "priority":    int(t.get("priority", 3)),
                "status":      t.get("status", "pending"),
                "depends_on":  t.get("depends_on", []),
                "parallel":    bool(t.get("parallel", False)),
            })

        cycle = _detect_cycle(tasks)
        if cycle:
            raise ValueError(
                f"[task_decompose] dependency cycle detected: {' → '.join(cycle)} → {cycle[0]}"
            )

        # Drain messages from queue that were addressed by this agent
        queue = state.get("user_message_queue", [])
        remaining = [m for m in queue if m.get("target_agent") not in ("task_decompose", "any")]

        return {
            **state,
            "tasks":    tasks,
            "tasks_md": data.get("tasks_md", ""),
            "user_message_queue": remaining,
        }

    # ── Tool definition (Mode A Anthropic SDK) ────────────────────────────────

    @property
    def tools(self) -> list[dict]:
        task_schema = {
            "type": "object",
            "properties": {
                "id":          {"type": "string"},
                "title":       {"type": "string"},
                "description": {"type": "string"},
                "phase":       {"type": "string", "enum": ["Setup", "Foundation", "Stories", "Polish"]},
                "priority":    {"type": "integer", "minimum": 1, "maximum": 5},
                "status":      {"type": "string", "enum": ["pending", "in_progress", "done"]},
                "depends_on":  {"type": "array", "items": {"type": "string"}},
                "parallel":    {"type": "boolean"},
            },
            "required": ["id", "title", "description", "phase", "priority", "status", "depends_on", "parallel"],
        }
        return [
            {
                "name": "submit_tasks",
                "description": "Submit the dependency-ordered task graph.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "tasks":    {"type": "array", "items": task_schema},
                        "tasks_md": {"type": "string", "description": "Markdown task list for specs/tasks.md"},
                        "summary":  {"type": "string"},
                    },
                    "required": ["tasks", "tasks_md", "summary"],
                },
            }
        ]
