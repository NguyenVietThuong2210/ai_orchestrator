# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An **AI Orchestrator** that coordinates four specialized AI agents to build software projects end-to-end:

| Agent | Role |
|---|---|
| **PM** | Breaks requirements into structured tasks, tracks progress |
| **Senior Analyser** | Produces technical specs, data/API contracts, risk analysis |
| **Senior Engineer** | Implements features based on Analyser's spec |
| **Senior QA** | Validates Engineer output against spec, reports defects |

## Architecture: LangGraph Supervisor

### Control Flow
```
User Request
    ↓
LangGraph Graph (deterministic routing — NOT an LLM)
    ├── dispatches agents in sequence via conditional_edges
    ├── pauses at human_gate (interrupt_before) — waits for spec approval
    ├── routes QA failures: minor → Engineer (max 3x), major → Analyser (max 2x)
    ├── checkpoints ProjectContext automatically via SqliteSaver/PostgresSaver
    └── always terminates: DONE (pass) or FAILED (max iterations hit)

Agent pipeline:
PM ──► Analyser ──[human_gate]──► Engineer ──► QA ──► DONE
                    ▲                  ▲              │ fail minor (≤3x)
                    │                  └──────────────┘
                    │                                 │ fail major (≤2x)
                    └─────────────────────────────────┘
                                                      │ any loop exhausted
                                                      ▼
                                                   FAILED
```

### Key Principle: Control Plane is Dumb
Routing is Python functions inside LangGraph `conditional_edges` — no LLM decides next state. Deterministic, testable, auditable.

### LangGraph Graph Definition
```python
from uuid import uuid4
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command

def human_gate(state: ProjectContext) -> ProjectContext:
    """Pause graph — resume only after explicit approve via API."""
    decision = interrupt({"spec": state["spec"], "prompt": "Approve spec to proceed?"})
    if decision != "approve":
        raise ValueError("Spec rejected by user")
    return state

def route_qa(state: ProjectContext) -> str:
    report = state["test_report"]
    if report.status == "pass":
        return "done"
    if report.status == "major":
        if state["qa_analyser_iteration"] >= MAX_QA_ANALYSER_ITERATIONS:
            return "failed"       # spec loop exhausted — stop, don't silently succeed
        return "analyser"
    # minor fail
    if state["iteration"] >= MAX_QA_ITERATIONS:
        return "failed"           # engineer loop exhausted
    return "engineer"

graph = StateGraph(ProjectContext)
graph.add_node("pm",         pm_agent.invoke)
graph.add_node("analyser",   analyser_agent.invoke)
graph.add_node("human_gate", human_gate)
graph.add_node("engineer",   engineer_agent.invoke)
graph.add_node("qa",         qa_agent.invoke)
graph.add_node("done",       handle_done)
graph.add_node("failed",     handle_failed)

graph.set_entry_point("pm")
graph.add_edge("pm",         "analyser")
graph.add_edge("analyser",   "human_gate")
graph.add_edge("human_gate", "engineer")
graph.add_edge("engineer",   "qa")
graph.add_conditional_edges("qa", route_qa, {
    "done":     "done",
    "failed":   "failed",
    "engineer": "engineer",
    "analyser": "analyser",
})
graph.add_edge("done",   END)
graph.add_edge("failed", END)

# interrupt_before pauses AT human_gate; resume() continues from checkpoint
app = graph.compile(
    checkpointer=SqliteSaver.from_conn_string(CHECKPOINT_DB),
    interrupt_before=["human_gate"],
)

# Every pipeline run: job_id == LangGraph thread_id (isolation between concurrent runs)
job_id = str(uuid4())
config  = {"configurable": {"thread_id": job_id}}

# Start
app.invoke(
    {"request": requirement, "iteration": 0, "qa_analyser_iteration": 0, "status": "running"},
    config,
)

# Resume after human approves spec (called by POST /approve_spec in FastAPI)
app.invoke(Command(resume="approve"), config)
```

## ProjectContext — Single Source of Truth

LangGraph state **must** be `TypedDict`, not `@dataclass`.

```python
from typing import TypedDict, Optional

class ProjectContext(TypedDict):
    request:                str                      # original user requirement
    job_id:                 str                      # = LangGraph thread_id
    tasks:                  list[Task]               # PM output
    spec:                   Optional[TechnicalSpec]  # Analyser output
    artifact_paths:         dict[str, str]           # filename → local path or S3 key
    test_report:            Optional[TestReport]     # QA output
    history:                list[AgentEvent]         # full audit log
    iteration:              int                      # QA→Engineer retry count
    qa_analyser_iteration:  int                      # QA→Analyser retry count
    status:                 str                      # "running" | "done" | "failed"
```

> **Artifact storage rule:** Engineer writes files to `ARTIFACT_DIR` (disk) or S3.
> `artifact_paths` stores only the path/key — never embed file content in the checkpoint.
> Large content in SQLite bloats checkpoint and breaks resume on big projects.

## Agent Contract

Every agent must implement:
- `system_prompt` — cached with `cache_control: {"type": "ephemeral"}`
- `invoke(state: ProjectContext) -> ProjectContext` — receives and returns full LangGraph state
- `tools` — role-scoped tool list (enforced by graph, not prompting)

### Role-Scoped Tools
| Agent | Allowed Tools |
|---|---|
| PM | `create_task`, `update_priority`, `submit_plan` |
| Analyser | `read_file`, `web_search`, `submit_spec` |
| Engineer | `read_file`, `write_file`, `run_shell`, `submit_implementation` |
| QA | `read_file`, `run_shell` (tests only), `submit_test_report` |

Each agent has one "submit" tool — it **must** call it to finish its turn. No freeform output reaches the graph.

## Integration Architecture

### REST API Backend (primary)
- FastAPI service exposing the orchestrator pipeline
- SSE endpoint streams via `app.astream_events()` — maps LangGraph events to SSE
- `job_id` (API) == `thread_id` (LangGraph config) — pass through every request

### MCP Server (VS Code / Claude Code integration)
```
Claude Code (VS Code) ──MCP──► MCP Server (Python/FastMCP) ──HTTP──► FastAPI Backend
```
Exposes three primitives:
- **Tools**: `run_pipeline`, `get_job_status`, `approve_spec`, `cancel_job`
- **Resources**: `project_spec`, `test_report`, `agent_logs`
- **Prompts**: `/build-feature`, `/review-spec`, `/run-qa`

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Runtime | Python 3.11+ | Async support, ecosystem |
| Orchestration | **LangGraph** | Built-in interrupt/checkpoint/resume, deterministic routing |
| Backend (Mode B) | `claude` CLI subprocess | No API key — Pro subscription auth, file tools built-in |
| Backend (Mode A) | Anthropic SDK direct | Full model selection, background/CI-CD ready |
| API | FastAPI + SSE | Async streaming of LangGraph events |
| MCP Server | FastMCP (Python) | ~60 lines, auto-schema from Pydantic |
| Observability | Langfuse (open source) | Trace all agent calls, token usage |
| Checkpoint (dev) | `SqliteSaver` | Zero setup, built into LangGraph |
| Checkpoint (prod) | `PostgresSaver` (pkg: `langgraph-checkpoint-postgres`) | Concurrent jobs, durability |
| Config | python-dotenv | Standard |
| **Frontend** | **React 18 + Vite + TypeScript + Tailwind CSS** | Pipeline control UI — form, real-time timeline, spec review, QA report |

## Directory Structure

```
ai_orchestrator/
├── orchestrator/
│   ├── graph.py           # LangGraph graph: nodes, edges, human_gate, route_qa, compile
│   ├── runner.py          # async loop: invoke/resume graph, stream events to FastAPI
│   └── context.py         # ProjectContext TypedDict + Task / TechnicalSpec / TestReport models
├── agents/
│   ├── base.py            # BaseAgent: invoke(), system_prompt, tools
│   ├── pm.py
│   ├── analyser.py
│   ├── engineer.py
│   └── qa.py
├── mcp_server/
│   └── server.py          # FastMCP server
├── api/
│   ├── main.py            # FastAPI app + StaticFiles mount (serves frontend/dist/)
│   ├── routes.py          # /run-pipeline, /status, /stream (SSE), /approve-spec, /cancel
│   └── schemas.py         # Pydantic I/O schemas
├── frontend/              # React SPA (Vite + TypeScript + Tailwind)
│   ├── src/
│   │   ├── App.tsx            # root layout: sidebar + state-driven main panel
│   │   ├── types/index.ts     # TypeScript types mirroring backend schemas
│   │   ├── api/client.ts      # typed fetch wrappers for all API routes
│   │   ├── hooks/
│   │   │   ├── useSSE.ts      # EventSource hook with auto-close
│   │   │   └── usePipeline.ts # pipeline state machine + polling
│   │   └── components/
│   │       ├── PipelineForm.tsx   # requirement textarea + Run/Cancel (cancelPending prop)
│   │       ├── AgentTimeline.tsx  # flat space-y-2 list; parent handles scroll
│   │       ├── SpecReview.tsx     # spec sections; showButtons=false hides inline btns
│   │       ├── ArtifactList.tsx   # engineer output file list
│   │       └── TestReport.tsx     # QA pass/fail/defect report
│   ├── package.json
│   ├── vite.config.ts         # dev proxy /api → :8000
│   └── dist/                  # production build (git-ignored, served by FastAPI)
├── artifacts/             # Engineer output (files written here, paths stored in checkpoint)
├── tools/                 # Claude tool definitions (JSON schema)
├── tests/
├── pyproject.toml
└── .env.example
```

## Development Commands

```bash
pip install -e ".[dev]"

# Run API backend
uvicorn api.main:app --reload

# Run MCP server (for VS Code integration)
python mcp_server/server.py

# Run full pipeline via CLI
python -m orchestrator.runner "Build a REST API for a todo app"

# Tests
pytest
pytest tests/test_pm_agent.py::test_task_breakdown -v

# Lint
ruff check . && ruff format .

# Frontend — development (hot reload, proxied to API :8000)
cd frontend && npm install && npm run dev
# → http://localhost:5173

# Frontend — production build (served by FastAPI at http://localhost:8000)
cd frontend && npm run build
uvicorn api.main:app --reload
```

## Environment Variables

```
# Backend: claude_code (Mode B, default) | api (Mode A)
AI_BACKEND=claude_code

# Mode A — requires ANTHROPIC_API_KEY
ANTHROPIC_API_KEY=sk-ant-...
PM_MODEL=claude-haiku-4-5-20251001
ANALYSER_MODEL=claude-opus-4-7
ENGINEER_MODEL=claude-sonnet-4-6
QA_MODEL=claude-sonnet-4-6

# Mode B — Pro subscription, override model per agent
PM_MODEL_B=claude-haiku-4-5-20251001
ANALYSER_MODEL_B=claude-sonnet-4-6
ENGINEER_MODEL_B=claude-sonnet-4-6
QA_MODEL_B=claude-sonnet-4-6

MAX_QA_ITERATIONS=3
MAX_QA_ANALYSER_ITERATIONS=2
HUMAN_GATE_TIMEOUT_HOURS=24
CHECKPOINT_DB=./data/checkpoints.sqlite
ARTIFACT_DIR=./artifacts
LOG_LEVEL=INFO
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
```

## Anthropic SDK — Prompt Caching Pattern

```python
response = client.messages.create(
    model=model,
    system=[{
        "type": "text",
        "text": agent.system_prompt,
        "cache_control": {"type": "ephemeral"}   # cache system prompt across turns
    }],
    messages=[
        {"role": "user", "content": [
            {"type": "text", "text": shared_context, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": specific_task}   # not cached — changes per call
        ]}
    ],
    tools=agent.tools,
    max_tokens=8096,
)
```

## Frontend — UI Architecture (Project Owner Dashboard)

The React SPA (`frontend/src/`) is a **project-owner dashboard**, not a chat UI. Layout:

```
┌─ Header ─────────────────────────────────────────────────────────────────┐
│  🤖 AI Orchestrator  [job-id copy btn]  [PM→Analyser→Review→Eng→QA bar]  [Status pill] │
├─ Sidebar (w-60) ──┬─ Agent Timeline (w-72) ─┬─ Right Panel (flex-1) ────┤
│  PipelineForm     │  Real-time event log     │  Tabs: Spec / QA / Files  │
│  Stat tiles       │  (history + SSE)         │                           │
│  PM Task board    │                          │  [Sticky Approve banner]  │
└───────────────────┴──────────────────────────┴───────────────────────────┘
```

### Key FE rules
- **Never call `setState` during render** — tab auto-switching uses `useEffect`, not inline conditionals.
- **Approve button** has a loading state (`approveLoading`) and is disabled while the request is in-flight.
- **Cancel** shows a `window.confirm` dialog before calling the API — prevents accidental clicks.
- **CopyButton** copies job ID to clipboard; displays truncated form in header.
- **TaskBoard** renders PM tasks with priority badge (P1/P2/P3), status dot, and description.
- **`SpecReview`** accepts `showButtons={false}` — approve/reject are in the sticky `ApprovalBanner`, not duplicated inline.
- **`AgentTimeline`** is a flat `<div className="space-y-2">` — the parent column handles overflow-y scroll.

### State machine (`usePipeline.ts`)
```
idle → starting → running ⇄ waiting_approval → running → done
                                                        → failed
```
- Polling (`setInterval 2500ms`) starts on `running`, stops at terminal states (`done | failed | waiting_approval`).
- After `approve()`, polling is manually restarted.
- SSE stream (`useSSE`) is active only when `status === "running"`.

## Known Issues & Constraints

### BE: `_jobs` registry is in-memory
`_jobs: dict[str, dict]` in `routes.py` is process-local. On server restart, all job IDs are lost → `/status` returns 404. **Production fix**: recover `_jobs` from SQLite checkpoint on startup, or persist to DB.

### BE: `SqliteSaver` — use `sqlite3.connect` directly (LangGraph 1.x)
`SqliteSaver.from_conn_string()` returns a **context-manager iterator**, NOT a `SqliteSaver`. Always construct via:
```python
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
checkpointer = SqliteSaver(conn)
```
Never call `SqliteSaver.from_conn_string(path)` without `with` — it silently produces a generator.

### BE: Mode B (ClaudeCodeBackend) — nested session guard
`claude -p` subprocesses fail with "Cannot be launched inside another Claude Code session" when the `CLAUDECODE` env var is set. Fix: strip `CLAUDECODE` from subprocess env:
```python
env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
proc = await asyncio.create_subprocess_exec(*cmd, env=env, ...)
```
This is already applied in `orchestrator/backends/claude_code_backend.py`.

### BE: `current_node` semantics
`snapshot.next` contains the **next** node to execute, not the currently running one. When no next node exists (`next == ()`), the route handler sets `current_node = "end"`. The frontend `NODE_TO_STEP` map ignores "end"; `getStepState` falls back gracefully.

### FE: `JobStatusResponse.tasks` must be included
`tasks` (PM output) must be in the API response for `TaskBoard` to render. It is declared in `schemas.py → JobStatusResponse` and populated in `routes.py → get_status` via `state.get("tasks", [])`.

## Enterprise Checklist

- [ ] Observability: Langfuse traces for every agent call (token usage, latency, cost)
- [ ] Cost guard: token budget per agent per run; alert when exceeded
- [ ] Human Gate: `interrupt_before=["human_gate"]` + auto-expire after `HUMAN_GATE_TIMEOUT_HOURS`
- [ ] Artifact storage: Engineer writes to `ARTIFACT_DIR` — never embed content in checkpoint
- [ ] MCP security: sanitize all inputs before forwarding to backend (prompt injection risk)
- [ ] Idempotency: LangGraph checkpoints after each node; `Command(resume=...)` continues from last checkpoint
- [ ] Max iteration guards: `MAX_QA_ITERATIONS` (engineer loop) + `MAX_QA_ANALYSER_ITERATIONS` (spec loop)
- [ ] FAILED terminal state: distinguish from DONE in API response, UI, and Langfuse
- [ ] Production checkpoint: swap `SqliteSaver` → `PostgresSaver` (`langgraph-checkpoint-postgres`)
- [ ] Concurrent isolation: always pass `thread_id=job_id` in LangGraph config
