# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Rules

- **Always update [SOLUTION.md](SOLUTION.md) after any code change** — document what changed, why, and which files were affected. SOLUTION.md is the living design record of this project.
- **Whenever SOLUTION.md is updated, also update [SOLUTION.html](SOLUTION.html)** — reflect the same changes in the Vietnamese customer presentation (changelog section at minimum).

## Project Overview

An **AI Orchestrator** that coordinates **10 specialized AI agents** to build software projects end-to-end, following a real SDLC with clarification, SDD speckit analysis, code review, security scanning, deployment verification, and retrospective.

**8 primary SDLC agents** — always present in the pipeline:

| Agent | Role |
|---|---|
| **PM** | Breaks requirements into structured tasks, outputs formal Definition of Done, flags ambiguous requirements, detects pipeline intent |
| **Analyser** | Produces technical specs, data/API contracts, risk analysis |
| **Engineer** | Implements features based on Analyser's spec |
| **Code Reviewer** | Reviews Engineer output against spec — catches design, correctness, and maintainability issues |
| **Security** | Runs bandit + pip-audit; classifies findings as pass/warn/fail |
| **QA** | Validates implementation against spec and DoD, reports defects |
| **Deploy** | Installs deps, starts server on port 9000, smoke-tests with curl |
| **Retrospective** | Analyzes full history + all reports; produces lessons learned regardless of outcome |

**2 SDD Speckit agents** — used for `feature` and `bug_fix` intent paths:

| Agent | Role |
|---|---|
| **SpecAnalyze** | Analyses Analyser's spec against SDD constitution; outputs spec_analysis with gaps and risks |
| **TaskDecompose** | Decomposes approved spec into fine-grained engineering tasks with acceptance criteria |

## Architecture: LangGraph Supervisor

### Control Flow

PM detects `pipeline_intent` from the request — routing is deterministic Python, no LLM decides next state.

```
User Request
    ↓
PM (detects intent: query | test | review | bug_fix | feature)
    │
    ├─ query  ──► Analyser ──► DONE
    ├─ test   ──► Analyser ──► QA ──► DONE / FAILED
    ├─ review ──► Analyser ──► Reviewer ──► DONE
    ├─ bug_fix──► [clarification?] ──► Analyser ──► Engineer ──► QA (≤3x) ──► DONE / FAILED
    │
    └─ feature ──► [clarification?] ──► Analyser ──► SpecAnalyze
                                                          ↓
                                                   [human_gate — spec approval]
                                                          ↓
                                                    TaskDecompose
                                                          ↓
                                                      Engineer ──► Reviewer ──► Security ──► QA ──► Deploy ──► Retrospective ──► DONE
                                                        ▲ (≤3x)                            │ fail minor (≤3x)
                                                        └───────────────────────────────────┘
                                                                ▲               │ fail major (≤2x)
                                                                └───────────────┘ (via Analyser → SpecAnalyze)
                                                                                │ security fail / deploy fail / loops exhausted
                                                                                ▼
                                                                          Retrospective ──► FAILED

Rules:
    ├── clarification_gate: in-node interrupt() — PM flags needs_clarification
    ├── human_gate: interrupt_before — waits for spec approve/reject (feature intent only)
    ├── security warn = pass-through; security fail → retrospective → FAILED
    ├── code review fail → Engineer retry (counts against MAX_QA_ITERATIONS)
    ├── deploy fail → retrospective → FAILED
    ├── checkpoints ProjectContext automatically via AsyncPostgresSaver
    └── always terminates via retrospective for feature/bug_fix: DONE or FAILED
```

### Key Principle: Control Plane is Dumb
Routing is Python functions inside LangGraph `conditional_edges` — no LLM decides next state. Deterministic, testable, auditable.

### LangGraph Graph Definition (condensed — feature intent path)

14 nodes: pm, clarification_gate, analyser, spec_analyze, human_gate, task_decompose, engineer, reviewer, security, qa, deploy, retrospective, done, failed.

Key routing functions:
```python
def route_pm(state):
    intent = state.get("pipeline_intent", "feature")
    if state.get("needs_clarification"): return "clarification_gate"
    if intent == "query": return "analyser_query"
    if intent in ("test", "review", "bug_fix"): return "analyser"
    return "analyser"  # feature → analyser → spec_analyze

def route_analyser(state):
    intent = state.get("pipeline_intent", "feature")
    if intent == "feature": return "spec_analyze"
    if intent == "bug_fix": return "engineer"
    if intent == "review": return "reviewer"
    if intent == "test": return "qa"
    return "done"  # query

def route_spec_analyze(state):
    # human_gate interrupt_before fires here for feature intent
    return "human_gate"

def route_reviewer(state):
    report = state.get("code_review_report")
    if not report or report["status"] == "pass": return "security"
    if state["iteration"] >= MAX_QA_ITERATIONS: return "retrospective"
    return "engineer"

def route_security(state):
    report = state.get("security_report")
    if report and report["status"] == "fail": return "retrospective"
    return "qa"  # pass or warn both proceed

def route_qa(state):
    report = state["test_report"]
    if report["status"] == "pass": return "deploy"
    if report["status"] == "fail-major":
        if state["qa_analyser_iteration"] >= MAX_QA_ANALYSER_ITERATIONS: return "retrospective"
        return "analyser"
    if state["iteration"] >= MAX_QA_ITERATIONS: return "retrospective"
    return "engineer"

def route_retrospective(state):
    return "done" if state.get("deploy_report", {}).get("status") == "pass" else "failed"

app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_gate"],  # clarification_gate uses in-node interrupt()
)
```

## ProjectContext — Single Source of Truth

LangGraph state **must** be `TypedDict`, not `@dataclass`.

```python
class ProjectContext(TypedDict):
    # ── Core ─────────────────────────────────────────────────────────────
    request:                  str
    job_id:                   str
    tasks:                    list[Task]
    spec:                     Optional[TechnicalSpec]
    artifact_paths:           dict[str, str]
    test_report:              Optional[TestReport]
    history:                  list[AgentEvent]
    iteration:                int                   # QA→Engineer retry count
    qa_analyser_iteration:    int                   # QA→Analyser retry count
    status:                   str                   # "running" | "done" | "failed"
    project_dir:              Optional[str]
    spec_dir:                 Optional[str]
    # ── PM / Clarification ────────────────────────────────────────────────
    pipeline_intent:          str                   # "query"|"test"|"review"|"bug_fix"|"feature"
    definition_of_done:       list[str]             # PM outputs; flows to all agents
    needs_clarification:      bool                  # PM flags ambiguous requirements
    clarification_questions:  list[str]             # PM's questions to user
    clarification_context:    str                   # user's answers (after clarification_gate)
    # ── SDD Speckit (feature/bug_fix intents) ─────────────────────────────
    constitution:             Optional[str]         # SDD constitutional governance text
    spec_md:                  Optional[str]         # raw markdown spec from Analyser
    plan_md:                  Optional[str]         # implementation plan markdown
    tasks_md:                 Optional[str]         # fine-grained task list
    checklist_md:             Optional[str]         # acceptance checklist
    spec_analysis:            Optional[dict]        # SpecAnalyze gaps + risks output
    spec_revision_count:      int                   # how many times spec was revised
    # ── Agent Reports ─────────────────────────────────────────────────────
    code_review_report:       Optional[CodeReviewReport]
    security_report:          Optional[SecurityReport]
    deploy_report:            Optional[DeployReport]
    retrospective:            Optional[Retrospective]
    # ── Multi-point Interaction ───────────────────────────────────────────
    user_message_queue:       list[str]             # injected messages pending consumption
    interaction_log:          list[dict]            # full log of user↔agent interactions
    pause_requested:          bool                  # user requested mid-pipeline pause
```

> **Artifact storage rule:** Engineer writes files to `projects/<name>/` (disk).
> `artifact_paths` stores only the path — never embed file content in the checkpoint.

## Agent Contract

Every agent must implement:
- `system_prompt` — cached with `cache_control: {"type": "ephemeral"}`
- `invoke(state: ProjectContext) -> ProjectContext` — receives and returns full LangGraph state

### Mode B Tool Access (ClaudeCodeBackend)
| Agent Set | Flag | Agents |
|---|---|---|
| Shell agents | `--dangerously-skip-permissions` | engineer, qa, security, deploy |
| Text-only agents | `--tools ""` | pm, analyser, reviewer, retrospective, spec_analyze, task_decompose |

### Role and Output
| Agent | Output field | Status values |
|---|---|---|
| PM | `tasks`, `definition_of_done`, `pipeline_intent`, `needs_clarification`, `clarification_questions` | — |
| Analyser | `spec`, `spec_md` | — |
| SpecAnalyze | `spec_analysis`, `constitution` | — |
| TaskDecompose | `plan_md`, `tasks_md`, `checklist_md` | — |
| Engineer | `artifact_paths`, `project_dir`, `spec_dir` | — |
| Reviewer | `code_review_report` | pass \| fail |
| Security | `security_report` | pass \| warn \| fail |
| QA | `test_report` | pass \| fail-minor \| fail-major |
| Deploy | `deploy_report` | pass \| fail |
| Retrospective | `retrospective` | — (always runs) |

## Integration Architecture

### REST API Backend (primary)
- FastAPI service exposing the orchestrator pipeline
- SSE endpoint streams via `app.astream_events()` — maps LangGraph events to SSE
- `job_id` (API) == `thread_id` (LangGraph config) — pass through every request

### API Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/run-pipeline` | Start new pipeline |
| POST | `/approve-spec` | Resume after human_gate (approve or reject) |
| POST | `/clarify/{job_id}` | Submit user answers to PM clarification questions |
| POST | `/resume/{job_id}` | Resume from last checkpoint (after crash/restart) |
| POST | `/cancel/{job_id}` | Cancel running pipeline |
| POST | `/pause/{job_id}` | Request mid-pipeline pause |
| POST | `/inject/{job_id}` | Inject a message into the running agent's context |
| POST | `/modify-spec/{job_id}` | Request spec modification mid-pipeline |
| GET | `/status/{job_id}` | Poll job state |
| GET | `/stream/{job_id}` | SSE live event stream |
| GET | `/jobs` | List recent jobs (used by UI auto-discover) |
| GET | `/solution` | Get latest solution/output |
| GET | `/artifact/{job_id}/{filename}` | Download a specific artifact file |
| GET | `/projects` | List all projects |
| GET | `/projects/{project_name}/runs` | List runs for a project |

### MCP Server (VS Code / Claude Code integration)
```
Claude Code (VS Code) ──MCP──► MCP Server (Python/FastMCP) ──HTTP──► FastAPI Backend
```
Exposes: `run_pipeline`, `get_job_status`, `approve_spec`, `cancel_job`, `clarify_job`

Resources: `project_spec`, `test_report`, `code_review_report`, `security_report`, `deploy_report`, `retrospective`, `agent_logs`

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
| Checkpoint | `AsyncPostgresSaver` | Concurrent jobs, durability, async-native |
| Config | python-dotenv | Standard |
| **Frontend** | **React 18 + Vite + TypeScript + Tailwind CSS** | 10-step pipeline dashboard with real-time SSE timeline |

## Directory Structure

```
ai_orchestrator/
├── orchestrator/
│   ├── graph.py           # LangGraph: 14 nodes, all routing functions, compile
│   ├── runner.py          # async invoke/resume, _initial_state (all fields)
│   └── context.py         # ProjectContext TypedDict + all TypedDicts
├── agents/
│   ├── base.py            # BaseAgent: build_prompt(), parse_submit(), system_prompt
│   ├── pm.py              # outputs tasks, DoD, pipeline_intent, clarification flag
│   ├── analyser.py        # outputs spec, spec_md
│   ├── spec_analyze.py    # SDD Speckit: analyses spec, outputs spec_analysis + constitution
│   ├── task_decompose.py  # SDD Speckit: decomposes spec into plan_md/tasks_md/checklist_md
│   ├── engineer.py        # outputs artifact_paths, project_dir, spec_dir
│   ├── reviewer.py        # code review (text-only), outputs code_review_report
│   ├── security.py        # bandit + pip-audit (shell), outputs security_report
│   ├── deploy.py          # install + start + smoke test (shell), outputs deploy_report
│   ├── retrospective.py   # lessons learned (text-only), always runs
│   └── __init__.py        # AGENTS dict with all 10 agents
├── orchestrator/backends/
│   ├── api_backend.py          # Mode A: Anthropic SDK direct
│   └── claude_code_backend.py  # Mode B: claude CLI subprocess, _SHELL_AGENTS/_TEXT_ONLY_AGENTS, budget guard
├── mcp_server/
│   └── server.py          # FastMCP server — 5 tools + 7 resources
├── api/
│   ├── main.py            # FastAPI app + StaticFiles mount
│   ├── routes.py          # all 15 endpoints incl. /inject /modify-spec /pause /artifact
│   ├── schemas.py         # Pydantic I/O schemas — all request/response types
│   └── project_store.py   # reads LangGraph checkpoints → ProjectBrowser data
├── frontend/              # React SPA (Vite + TypeScript + Tailwind, Jira/Linear dark theme)
│   ├── src/
│   │   ├── App.tsx            # PipelineBar, 6 grouped tabs, ClarificationModal, ApprovalModal
│   │   ├── types/index.ts     # TypeScript types (all report interfaces, ProjectContext)
│   │   ├── api/client.ts      # all API calls (clarify, inject, modify-spec, approve, cancel…)
│   │   ├── hooks/
│   │   │   ├── usePipeline.ts # state machine + all user actions
│   │   │   └── useProjects.ts # projects browser data fetching
│   │   └── components/
│   │       ├── AgentTimeline.tsx   # real-time event log, colors for all 10 agents
│   │       ├── ProjectsBrowser.tsx # sidebar projects list + run history
│   │       └── StatusBadge.tsx     # all statuses incl. waiting_clarification (purple)
│   └── dist/              # production build (served by FastAPI)
├── projects/              # all Engineer output (unified root per project)
├── tests/
├── pyproject.toml
└── .env.example
```

## Development Commands

```bash
pip install -e ".[dev]"

# Run API backend (watches all source dirs)
python -m api.main

# Run MCP server (for VS Code integration)
python mcp_server/server.py

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
python -m api.main
```

## Environment Variables

```
# ── Required ─────────────────────────────────────────────────────────────────
DATABASE_URL=postgresql://user:pass@localhost:5432/orchestrator

# ── Agent backend ─────────────────────────────────────────────────────────────
AI_BACKEND=claude_code          # "claude_code" (Mode B) | "api" (Mode A)

# Mode A — requires API key
ANTHROPIC_API_KEY=sk-ant-...
PM_MODEL=claude-haiku-4-5-20251001
ANALYSER_MODEL=claude-opus-4-7
ENGINEER_MODEL=claude-sonnet-4-6
REVIEWER_MODEL=claude-haiku-4-5-20251001
SECURITY_MODEL=claude-sonnet-4-6
QA_MODEL=claude-sonnet-4-6
DEPLOY_MODEL=claude-sonnet-4-6
RETROSPECTIVE_MODEL=claude-haiku-4-5-20251001

# Mode B — Claude Pro subscription
PM_MODEL_B=claude-haiku-4-5-20251001
ANALYSER_MODEL_B=claude-sonnet-4-6
ENGINEER_MODEL_B=claude-sonnet-4-6
REVIEWER_MODEL_B=claude-haiku-4-5-20251001
SECURITY_MODEL_B=claude-sonnet-4-6
QA_MODEL_B=claude-sonnet-4-6
DEPLOY_MODEL_B=claude-sonnet-4-6
RETROSPECTIVE_MODEL_B=claude-haiku-4-5-20251001

# ── Pipeline limits ───────────────────────────────────────────────────────────
MAX_QA_ITERATIONS=3
MAX_QA_ANALYSER_ITERATIONS=2
MAX_TOKENS_PER_AGENT=0          # 0 = disabled; set e.g. 50000 to cap per-agent spend

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECTS_ROOT=./projects

# ── Observability (optional) ──────────────────────────────────────────────────
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
        "cache_control": {"type": "ephemeral"}
    }],
    messages=[
        {"role": "user", "content": [
            {"type": "text", "text": shared_context, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": specific_task}
        ]}
    ],
    max_tokens=8096,
)
```

## Frontend — UI Architecture (Project Owner Dashboard)

Jira/Linear dark theme. 2-column layout.

```
┌─ Header ─────────────────────────────────────────────────────────────────────────────────────────┐
│  AI Orchestrator  [job-id]  [PipelineBar: PM→Clarify→Analyser→SpecAnalyze→Approve→TaskDecompose  │
│                              →Eng→Review→Sec→QA→Deploy→Retro]  [Status Badge]                    │
├─ Sidebar (w-80) ───────────────────┬─ Main Panel (flex-1) ─────────────────────────────────────┤
│  PipelineForm (new run)            │  6 grouped tabs:                                            │
│  ProjectsBrowser (project list)    │    Live (AgentTimeline SSE) | Plan (SDD plan_md/tasks_md)  │
│  AgentTimeline (w-72, event log)   │    Spec (spec_md, constitution) | Code (artifact browser)  │
│                                    │    Quality (review+security+QA+deploy reports)              │
│                                    │    Outcome (retrospective)                                  │
│                                    │  [ClarificationModal — floating, status=waiting_clarif.]    │
│                                    │  [ApprovalModal — floating, status=waiting_approval]        │
└────────────────────────────────────┴────────────────────────────────────────────────────────────┘
```

### Key FE rules
- **Never call `setState` during render** — tab auto-switching uses `useEffect`.
- **ClarificationModal** shown when `status === "waiting_clarification"` — user answers PM questions.
- **ApprovalModal** shown when `status === "waiting_approval"` — approve/reject spec.
- **Approve/Clarify buttons** have loading states and are disabled while in-flight.
- **Cancel** shows `window.confirm` before calling API.
- `AgentTimeline` colors: pm=purple, analyser=blue, spec_analyze=cyan, task_decompose=violet, engineer=orange, reviewer=yellow, security=red, qa=green, deploy=teal, retrospective=indigo.

### State machine (`usePipeline.ts`)
```
idle → starting → running ⇄ waiting_clarification → running
                          ⇄ waiting_approval      → running → done
                                                            → failed
```
- Terminal statuses (polling stops): `done | failed | waiting_approval | waiting_clarification`
- SSE stream active only when `status === "running"`
- Auto-discover: polls `/jobs` every 3s when idle; prefers `waiting_clarification` > `waiting_approval` > `running`
- ProjectsBrowser: fetches `/projects` + `/projects/{name}/runs` for archive view

## Known Issues & Constraints

### BE: `_jobs` registry is in-memory
`_jobs: dict[str, dict]` in `routes.py` is process-local. On server restart, all job IDs are lost → `/status` may 404.
LangGraph state is safely in PostgreSQL. Resume via `POST /resume/{job_id}`.

### BE: `asyncio.Task` references not persisted
If server restarts mid-pipeline, the task is gone but LangGraph checkpoint remains. Use `POST /resume/{job_id}` to continue.

### BE: Mode B — Windows `.cmd` resolution
`asyncio.create_subprocess_exec` cannot resolve `.cmd` via `PATHEXT`. Fixed: `claude.cmd` explicit on Windows.

### BE: Mode B — nested session guard
`claude -p` subprocesses fail inside Claude Code sessions if `CLAUDECODE` env var is set. Fixed: strip `CLAUDECODE` from subprocess env.

### BE: `current_node` semantics
`snapshot.next` is the **next** node, not the currently-running one. Frontend `NODE_TO_STEP` map handles this gracefully.

### BE: `DATABASE_URL` is required
Server raises `RuntimeError` at startup if unset. No SQLite fallback.

### BE: Security `warn` is pass-through
`security_report.status == "warn"` proceeds to QA with findings logged. Only `"fail"` blocks the pipeline.

### FE: New report fields may be null
`code_review_report`, `security_report`, `deploy_report`, `retrospective` are all `null` until the respective agent runs. All UI panels guard with `?? []` and null checks.

### BE: CORS locked to explicit origins
`CORS_ORIGINS` env var controls allowed origins. Defaults: `http://localhost:5173,http://localhost:8000`.

### BE: Idempotency guards on all resume endpoints
`/approve-spec`, `/clarify/{job_id}`, `/resume/{job_id}` all check for in-flight tasks before spawning a second asyncio task.

### BE: Subprocess secret filtering
`claude_code_backend.py` strips `CLAUDECODE`, `DATABASE_URL`, `ANTHROPIC_API_KEY`, `LANGFUSE_*` from subprocess env.

## Enterprise Checklist

- [ ] Observability: Langfuse traces for every agent call (token usage, latency, cost)
- [x] Cost guard: `MAX_TOKENS_PER_AGENT` env var — raises RuntimeError if exceeded
- [x] Clarification loop: PM flags ambiguous requirements; user answers via UI before Analyser runs
- [x] Human Gate: `interrupt_before=["human_gate"]` — waits for spec approval
- [x] Code Review: dedicated Reviewer agent between Engineer and Security
- [x] Security scanning: bandit + pip-audit via Security agent; warn = pass-through, fail = block
- [x] Deploy verification: Deploy agent starts server and smoke-tests endpoint
- [x] Retrospective: always runs regardless of outcome (lessons learned every run)
- [x] Artifact storage: Engineer writes to `projects/<name>/` — never embed content in checkpoint
- [x] MCP security: sanitize all inputs before forwarding to backend
- [x] Idempotency: LangGraph checkpoints after each node; all resume endpoints guard against double-spawn
- [x] Max iteration guards: `MAX_QA_ITERATIONS` + `MAX_QA_ANALYSER_ITERATIONS`
- [x] FAILED terminal state: distinct from DONE in API, UI status badge, and routing
- [ ] Job registry persistence: recover `_jobs` from Postgres on server restart
- [x] Concurrent isolation: `thread_id=job_id` in every LangGraph config
