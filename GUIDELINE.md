# AI Orchestrator — Usage Guideline

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Environment Configuration](#3-environment-configuration)
4. [Running the Pipeline](#4-running-the-pipeline)
   - [Option 1 — MCP Server · VS Code / Claude Code ⭐ recommended](#41-option-1--mcp-server--vs-code--claude-code--recommended)
   - [Option 2 — Claude Code Agent CLI](#42-option-2--claude-code-agent-cli)
   - [Option 3 — REST API](#43-option-3--rest-api)
   - [Option 4 — Python CLI](#44-option-4--python-cli)
5. [Human Gate — Approval Flow](#5-human-gate--approval-flow)
6. [Checkpoint & Resume](#6-checkpoint--resume)
7. [Environment Variable Reference](#7-environment-variable-reference)
8. [Frontend UI](#8-frontend-ui)
9. [Running Tests](#9-running-tests)
10. [Troubleshooting](#10-troubleshooting)
11. [End-to-End Example: Django Hello App](#11-end-to-end-example-django-hello-app)

---

## 1. Prerequisites

| Requirement | Minimum version | Notes |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Claude Code CLI | latest | `npm i -g @anthropic-ai/claude-code` then `claude --version` |
| Claude Code Pro subscription | — | Mode B uses the CLI; an active subscription is required |
| Node.js | 18+ | Required by Claude Code CLI |
| Git | any | Optional — only needed for artifact versioning |

> **Mode A (API)**: Set `AI_BACKEND=api` and provide `ANTHROPIC_API_KEY`. No Claude Code CLI needed.  
> **Mode B (Claude Code CLI, default)**: Set `AI_BACKEND=claude_code` (or leave unset). Claude Pro subscription required.

---

## 2. Installation

```bash
# 1. Clone / enter the project
cd d:/New-jouney/ai_orchestrator

# 2. Install with dev dependencies
pip install -e ".[dev]"

# 3. Copy the example env file and fill in your values
copy .env.example .env
```

Verify the install:

```bash
python -c "import orchestrator; print('OK')"
pytest --tb=short          # should show 33 passed, 0 failed
```

---

## 3. Environment Configuration

Copy `.env.example` to `.env` and edit:

```dotenv
# ── Backend mode ────────────────────────────────────────────────────
AI_BACKEND=claude_code          # "claude_code" (Mode B) | "api" (Mode A)

# ── Mode A — Anthropic API (only needed when AI_BACKEND=api) ────────
ANTHROPIC_API_KEY=sk-ant-...

PM_MODEL_A=claude-haiku-4-5-20251001
ANALYSER_MODEL_A=claude-opus-4-7
ENGINEER_MODEL_A=claude-sonnet-4-6
QA_MODEL_A=claude-sonnet-4-6

# ── Mode B — Claude Code CLI ─────────────────────────────────────────
PM_MODEL_B=claude-haiku-4-5-20251001
ANALYSER_MODEL_B=claude-sonnet-4-6
ENGINEER_MODEL_B=claude-sonnet-4-6
QA_MODEL_B=claude-sonnet-4-6

# ── Orchestrator tuning ──────────────────────────────────────────────
MAX_QA_ITERATIONS=3             # max Engineer retries before pipeline fails
CHECKPOINT_DB=./data/checkpoints.sqlite

# ── Observability (optional) ─────────────────────────────────────────
# LANGFUSE_PUBLIC_KEY=...
# LANGFUSE_SECRET_KEY=...
LOG_LEVEL=INFO
```

> All model settings are read **at runtime** (after `load_dotenv()`), so you can change them without restarting the interpreter.

---

## 4. Running the Pipeline

> **Priority order:** MCP → Agent CLI → REST API → Python CLI.  
> MCP and Agent CLI are the primary interfaces — they integrate directly into your editor workflow without switching context.

---

### 4.1 Option 1 — MCP Server · VS Code / Claude Code ⭐ recommended

The MCP server exposes the orchestrator as tools inside Claude Code (VS Code extension or desktop app). You interact in plain language — Claude calls the tools for you.

**Step 1 — Start the backend**

```bash
uvicorn api.main:app --reload --port 8000
```

**Step 2 — Register the MCP server**

Create or update `.mcp.json` in the project root:

```json
{
  "mcpServers": {
    "ai-orchestrator": {
      "command": "python",
      "args": ["mcp_server/server.py"],
      "cwd": "d:/New-jouney/ai_orchestrator"
    }
  }
}
```

Restart Claude Code. The tools appear automatically.

**Step 3 — Use in Claude Code**

Just talk to Claude:

```
Run the pipeline: build a Django hello-world app in projects/hello_django/
```

Claude calls `run_pipeline` → streams back status → pauses when the spec is ready → asks you to review → calls `approve_spec` when you say yes.

**Available MCP primitives:**

| Type | Name | What it does |
|---|---|---|
| Tool | `run_pipeline` | Start a new pipeline with a requirement |
| Tool | `get_job_status` | Check status, read spec, history, test report |
| Tool | `approve_spec` | Approve the Analyser spec → start Engineering |
| Tool | `cancel_job` | Cancel a running job |
| Resource | `project_spec` | Read the current technical spec |
| Resource | `test_report` | Read the QA test report |
| Resource | `agent_logs` | Read the full agent event history |
| Prompt | `/build-feature` | Guided prompt to start a feature build |
| Prompt | `/review-spec` | Guided prompt to review a pending spec |
| Prompt | `/run-qa` | Guided prompt to trigger a QA pass |

**Human Gate via MCP:**

When the pipeline pauses at Human Gate, Claude will show you the spec and ask for approval. Say:

```
Looks good, approve it.
```

Claude calls `approve_spec` → Engineering starts automatically.

To reject:

```
Reject — the spec is missing authentication.
```

---

### 4.2 Option 2 — Claude Code Agent CLI

Run the orchestrator as a Claude Code sub-agent directly from your terminal. This is the fastest way to kick off a pipeline without opening a browser or editor.

**Prerequisite:** Claude Code CLI installed and logged in.

```bash
# Make sure the Claude Code session is active
claude --version

# Run the orchestrator as a sub-agent (Mode B)
claude -p "Run the AI orchestrator pipeline with this requirement:
Build a Django hello-world app in projects/hello_django/.
Use the orchestrator tool: run_pipeline." \
  --mcp-config .mcp.json
```

Or use the built-in `/build-feature` prompt:

```bash
claude --mcp-config .mcp.json
# Inside the session:
/build-feature
```

Claude will ask for the requirement, call `run_pipeline`, stream events, pause at Human Gate, and wait for your approval — all inside the terminal session.

**Approve from the same session:**

```
/review-spec
# Claude shows the spec, you say "approve"
```

---

### 4.3 Option 3 — REST API

For programmatic access, CI/CD pipelines, or the Frontend UI.

```bash
uvicorn api.main:app --reload --port 8000
```

**Start a pipeline**

```bash
curl -X POST http://localhost:8000/run-pipeline \
  -H "Content-Type: application/json" \
  -d '{"requirement": "Build a REST API for a todo app"}'
```

```json
{ "job_id": "a1b2c3d4", "status": "started" }
```

**Poll status**

```bash
curl http://localhost:8000/status/a1b2c3d4
```

```json
{
  "job_id": "a1b2c3d4",
  "status": "waiting_approval",
  "spec": { "overview": "..." }
}
```

**Approve**

```bash
curl -X POST http://localhost:8000/approve-spec \
  -H "Content-Type: application/json" \
  -d '{"job_id": "a1b2c3d4", "decision": "approve"}'
```

**Stream real-time events (SSE)**

```bash
curl -N http://localhost:8000/stream/a1b2c3d4
```

Full API docs: `http://localhost:8000/docs`

---

### 4.4 Option 4 — Python CLI

Quickest way to test the pipeline locally without any server.

```bash
# Start a new run
python -m orchestrator.runner "Build a REST API for a todo app"

# Resume a paused job (e.g. after Human Gate)
python -m orchestrator.runner "" --job-id a1b2c3d4
```

Output:

```
[PM]        ✓  3 tasks created
[Analyser]  ✓  technical spec ready
⏸  Human Gate — job_id: a1b2c3d4
   Spec overview: Minimal REST API with CRUD endpoints...

Approve spec? [approve/reject]: approve

[Engineer]  ✓  6 files written
[QA]        ✓  all checks passed
✅ Pipeline DONE
```

---

## 5. Human Gate — Approval Flow

The pipeline **always pauses** after the Analyser writes the technical spec, before any code is written. This is your only chance to correct the direction before Engineering starts.

```
PM → Analyser → ⏸ PAUSE (you review spec here) → Engineer → QA → DONE
```

### What you see at each interface

| Interface | How the pause appears |
|---|---|
| **MCP / Claude Code** | Claude presents the spec in chat and asks for your decision |
| **Agent CLI** | Claude outputs the spec and prompts `/review-spec` |
| **Frontend UI** | Main panel switches to "Spec Review" with Approve / Reject buttons |
| **REST API** | `GET /status/{job_id}` returns `"status": "waiting_approval"` + full spec |
| **Python CLI** | Prints spec overview, prompts `[approve/reject]:` |

### Approve — start Engineering

**MCP / Agent CLI:** say `"approve"` or `"looks good, proceed"` in the chat.

**Frontend UI:** click the green **Approve — Start Engineering ▶** button.

**REST API:**
```bash
curl -X POST http://localhost:8000/approve-spec \
  -H "Content-Type: application/json" \
  -d '{"job_id": "<job_id>", "decision": "approve"}'
```

**Python CLI:** type `approve` at the prompt.

### Reject — cancel and restart

**MCP / Agent CLI:** say `"reject"` or describe what's wrong — Claude will call `cancel_job`.

**Frontend UI:** click **Reject & Cancel**.

**REST API:**
```bash
curl -X POST http://localhost:8000/approve-spec \
  -H "Content-Type: application/json" \
  -d '{"job_id": "<job_id>", "decision": "reject"}'
```

> The job is checkpointed at the pause point. If you close everything and come back later, the spec is still there — just call approve/reject when ready.

---

## 6. Checkpoint & Resume

Every agent step is checkpointed to SQLite automatically. If the pipeline crashes, the session closes, or you shut everything down — resume from the exact same node without restarting from scratch.

**MCP / Agent CLI:**

```
Resume job a1b2c3d4
```

Claude calls `run_pipeline` with the existing `job_id` → LangGraph resumes from the last checkpoint.

**Python CLI:**

```bash
python -m orchestrator.runner "" --job-id <job_id>
```

**REST API:**

```bash
curl -X POST http://localhost:8000/run-pipeline \
  -H "Content-Type: application/json" \
  -d '{"requirement": "", "job_id": "<job_id>"}'
```

Checkpoint file: `./data/checkpoints.sqlite` (change with `CHECKPOINT_DB` in `.env`).

---

## 7. Environment Variable Reference

| Variable | Default | Description |
|---|---|---|
| `AI_BACKEND` | `claude_code` | `claude_code` or `api` |
| `ANTHROPIC_API_KEY` | — | Required for Mode A only |
| `PM_MODEL_A` | `claude-haiku-4-5-20251001` | PM model, Mode A |
| `ANALYSER_MODEL_A` | `claude-opus-4-7` | Analyser model, Mode A |
| `ENGINEER_MODEL_A` | `claude-sonnet-4-6` | Engineer model, Mode A |
| `QA_MODEL_A` | `claude-sonnet-4-6` | QA model, Mode A |
| `PM_MODEL_B` | `claude-haiku-4-5-20251001` | PM model, Mode B |
| `ANALYSER_MODEL_B` | `claude-sonnet-4-6` | Analyser model, Mode B |
| `ENGINEER_MODEL_B` | `claude-sonnet-4-6` | Engineer model, Mode B |
| `QA_MODEL_B` | `claude-sonnet-4-6` | QA model, Mode B |
| `MAX_QA_ITERATIONS` | `3` | Max Engineer retries before pipeline fails |
| `CHECKPOINT_DB` | `./data/checkpoints.sqlite` | SQLite checkpoint path |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` |
| `LANGFUSE_PUBLIC_KEY` | — | Observability (optional) |
| `LANGFUSE_SECRET_KEY` | — | Observability (optional) |

---

## 8. Frontend UI

A React SPA built with Vite + TypeScript + Tailwind CSS. It provides:
- **Requirement form** — enter a prompt and click Run
- **Real-time agent timeline** — streams SSE events as each agent works
- **Spec review panel** — displays the Analyser's technical spec with Approve / Reject buttons (Human Gate)
- **QA report** — shows passed/failed tests and defect list
- **Artifact list** — lists all files written by the Engineer

### Layout

```
┌────────────────────────────────────────────────────────┐
│  🤖 AI Orchestrator          [job-id]   [status]  Docs │  ← header
├──────────────────┬─────────────────────────────────────┤
│  New Pipeline    │                                     │
│  ─────────────   │  idle      → welcome / agent cards  │
│  [requirement    │  running   → real-time timeline     │
│   textarea]      │  approval  → spec review + buttons  │
│                  │  done      → QA report + artifacts  │
│  [Run ▶]        │  failed    → error + last QA report  │
│  ─────────────   │                                     │
│  Steps           │                                     │
│  ✓ PM            │                                     │
│  ✓ Analyser      │                                     │
│  · Review        │                                     │
│  · Engineer      │                                     │
│  · QA            │                                     │
└──────────────────┴─────────────────────────────────────┘
```

### Development mode (hot reload)

```bash
# Terminal 1 — start API backend
uvicorn api.main:app --reload --port 8000

# Terminal 2 — start Vite dev server
cd frontend
npm install      # first time only
npm run dev
# → http://localhost:5173
```

Vite proxies all API calls (`/run-pipeline`, `/status/*`, `/stream/*`, etc.) to `http://localhost:8000` automatically — no CORS issues.

### Production mode (served by FastAPI)

```bash
cd frontend
npm run build        # outputs to frontend/dist/

cd ..
uvicorn api.main:app --reload
# → http://localhost:8000   (serves the React app)
# → http://localhost:8000/docs  (FastAPI Swagger, still accessible)
```

FastAPI detects `frontend/dist/` at startup and mounts it as static files. All non-API paths return `index.html` (SPA fallback).

### Frontend file structure

```
frontend/
├── src/
│   ├── App.tsx                 # sidebar layout + state-driven main panel
│   ├── types/index.ts          # TypeScript types mirroring backend schemas
│   ├── api/client.ts           # typed fetch wrappers (runPipeline, approveSpec, …)
│   ├── hooks/
│   │   ├── useSSE.ts           # EventSource with auto-close on stream_end
│   │   └── usePipeline.ts      # state machine: idle→starting→running→approval→done/failed
│   └── components/
│       ├── StatusBadge.tsx
│       ├── PipelineForm.tsx    # textarea + Run/Cancel
│       ├── AgentTimeline.tsx   # SSE events + polling history
│       ├── SpecReview.tsx      # overview, components, API contracts, Approve/Reject
│       ├── ArtifactList.tsx    # engineer output files
│       └── TestReport.tsx      # pass/fail/defects
├── package.json
├── vite.config.ts
└── tsconfig.json
```

---

## 9. Running Tests

```bash
# All tests (33 total, offline — no claude CLI or API required)
pytest

# Verbose output
pytest -v

# Single test file
pytest tests/test_backends.py -v
pytest tests/test_graph.py -v
pytest tests/test_context.py -v

# Single test
pytest tests/test_backends.py::test_get_model_defaults -v

# Lint
ruff check .
ruff format --check .
```

**Test coverage:**

| File | What is tested |
|---|---|
| `test_backends.py` | Model selection, `_extract_submit_data`, `build_prompt`, `parse_submit` |
| `test_graph.py` | `route_qa` routing, `handle_done/failed`, agent `parse_submit` |
| `test_context.py` | `ProjectContext` TypedDict structure |

All tests are **fully offline** — no subprocess or API call is made.

---

## 10. Troubleshooting

### `No <submit> block found in output`

The Claude Code CLI response did not include the required `<submit>...</submit>` JSON block.

**Cause:** The model ran out of context, was interrupted, or the prompt was misunderstood.

**Fix:**
- Re-run the pipeline (checkpoint resumes from the failed node).
- For persistent failures, upgrade the model (`ANALYSER_MODEL_B=claude-sonnet-4-6` → `claude-opus-4-7`).
- Check `LOG_LEVEL=DEBUG` output for the raw claude output.

---

### `json.JSONDecodeError` inside `<submit>` block

The model produced malformed JSON inside the submit block.

**Fix:** Same as above — retry or upgrade model. With `LOG_LEVEL=DEBUG` you can see the raw output.

---

### `claude: command not found`

Claude Code CLI is not installed or not on `PATH`.

```bash
npm i -g @anthropic-ai/claude-code
claude --version
```

---

### `Session closed` / `Rate limit exceeded`

Claude Code Pro has session/rate limits.

**Fix:** Wait a few minutes and re-run. The checkpoint will resume from where it stopped.

---

### `ModuleNotFoundError: No module named 'orchestrator'`

The package is not installed in the current Python environment.

```bash
pip install -e ".[dev]"
```

Or run from the project root with:

```bash
PYTHONPATH=. python -m orchestrator.runner "..."
```

---

### Pipeline status stuck at `waiting_approval`

The Human Gate is paused and waiting for your explicit approval. Use whichever interface you started with:

**MCP / Agent CLI:** say `"approve"` in the chat session.

**Frontend UI:** click the green **Approve — Start Engineering ▶** button.

**REST API:**
```bash
curl -X POST http://localhost:8000/approve-spec \
  -H "Content-Type: application/json" \
  -d '{"job_id": "<job_id>", "decision": "approve"}'
```

---

### `iteration` keeps hitting `MAX_QA_ITERATIONS`

The Engineer and QA are in a fail loop.

**Diagnose:**
1. `GET /status/{job_id}` — check `test_report.defects` for recurring defects.
2. `GET /status/{job_id}` → `history` — check what the Engineer is doing each iteration.

**Fix options:**
- Increase `MAX_QA_ITERATIONS` temporarily.
- Add more detail to the original request.
- Upgrade `ENGINEER_MODEL_B` to a more capable model.

---

### `SqliteSaver` checkpoint database locked

Another process has the SQLite file open.

**Fix:** Stop all orchestrator processes and retry. Or set a different `CHECKPOINT_DB` path.

---

## Pipeline Status Reference

| Status | Meaning |
|---|---|
| `running` | Pipeline is actively executing an agent |
| `waiting_approval` | Paused at Human Gate — awaiting your approval |
| `done` | All agents completed; artifacts are available |
| `failed` | Max iterations exceeded or unrecoverable error |

---

## 11. End-to-End Example: Django Hello App

**Goal:** Build a minimal Django "Hello World" app, output saved under `projects/hello_django/`.

This walks through every pipeline step — what happens internally, what you see on screen, and how to verify each stage is complete.

---

### Overview: How your prompt maps to the pipeline

```
Your prompt
    │
    ▼
[PM Agent]          → breaks requirement into tasks
    │
    ▼
[Analyser Agent]    → writes technical spec (Django project layout, views, urls)
    │
    ▼
[Human Gate]        ← YOU review + approve the spec here
    │
    ▼
[Engineer Agent]    → writes all files into projects/hello_django/
    │
    ▼
[QA Agent]          → runs django-admin check, verifies files exist, tests view
    │
    ├── pass  → DONE  ✓
    └── fail  → Engineer retries (up to 3×), then FAILED
```

Each agent produces a structured JSON output via `<submit>` — the LangGraph router reads it and decides the next node. **No LLM decides routing** — it is plain Python.

---

### Step 0 — Prepare the output folder

```bash
# From the orchestrator root
mkdir -p projects/hello_django
```

Set `ARTIFACT_DIR` in `.env` so the Engineer writes there:

```dotenv
ARTIFACT_DIR=./projects
```

> The Engineer agent writes files to `{ARTIFACT_DIR}/{project_name}/`. Paths are recorded in `artifact_paths` inside the checkpoint — never the file content itself.

---

### Step 1 — Start the pipeline

Choose your preferred interface:

**⭐ MCP (recommended) — inside Claude Code:**
```
Run the AI orchestrator pipeline:
Build a minimal Django "Hello World" web app.
Store all files under projects/hello_django/.
The app must have one view at / that returns "Hello, World!"
and must be runnable with: python manage.py runserver
```
Claude calls `run_pipeline` and streams status back in the chat.

**Agent CLI:**
```bash
claude --mcp-config .mcp.json
# Then inside the session:
/build-feature
# Enter the requirement when prompted
```

**Python CLI (no server needed):**
```bash
python -m orchestrator.runner \
  "Build a minimal Django 'Hello World' web app. \
   Store all files under projects/hello_django/. \
   The app must have one view at / that returns 'Hello, World!' \
   and must be runnable with: python manage.py runserver"
```

**What you see (all interfaces):**

```
[PM]       ✓  3 tasks created  (1.4 s)
[Analyser] ✓  spec ready       (8.2 s)
⏸  Human Gate — spec is ready for your review
   Job ID: f3a8b21c
```

**How to verify PM is done:**  
Tasks list populated — check via MCP tool or API:

```bash
# MCP: ask Claude "what are the tasks for job f3a8b21c?"
# API:
curl http://localhost:8000/status/f3a8b21c | python -m json.tool
```

Look for `"tasks": [ {...}, {...}, {...} ]` — three items with `"status": "pending"`.

**How PM maps to the flow:**  
PM runs first (`set_entry_point("pm")`). It calls `parse_submit()` which writes the task list into `ProjectContext.tasks`. LangGraph then routes automatically to `analyser` via a fixed edge.

---

### Step 2 — Review the technical spec (Human Gate)

The pipeline is **paused**. The Analyser has written a spec but Engineering has not started yet.

Read the spec:

```bash
curl http://localhost:8000/status/f3a8b21c | python -m json.tool
```

Expected `spec` block (abbreviated):

```json
{
  "overview": "Minimal Django app with a single / endpoint returning 'Hello, World!'",
  "components": [
    { "name": "hello_django/", "description": "Django project root" },
    { "name": "hello/views.py", "description": "HelloView returning HttpResponse" },
    { "name": "hello/urls.py",  "description": "URL conf wiring / to HelloView" }
  ],
  "api_contracts": [
    { "method": "GET", "path": "/", "response": "200 Hello, World!" }
  ],
  "data_models": [],
  "risks": [
    { "id": "R1", "description": "manage.py runserver uses development server — not production-ready" }
  ],
  "acceptance_criteria": [
    "GET / returns HTTP 200 with body 'Hello, World!'",
    "python manage.py check exits 0",
    "project structure matches Django conventions"
  ]
}
```

**How to verify Analyser is done:**  
`"status": "waiting_approval"` in the status response. `spec` field is non-null.

**How Analyser maps to the flow:**  
`analyser` node calls `parse_submit()` → writes `ProjectContext.spec`. LangGraph routes to `human_gate` via fixed edge. `interrupt_before=["human_gate"]` pauses the graph **before** entering that node — the checkpoint is saved at this exact moment.

**If the spec looks wrong** — reject and re-run with a more detailed prompt:

```
# MCP: tell Claude "reject the spec for job f3a8b21c"
# API:
curl -X POST http://localhost:8000/approve-spec \
  -H "Content-Type: application/json" \
  -d '{"job_id": "f3a8b21c", "decision": "reject"}'
```

---

### Step 3 — Approve and start Engineering

**MCP (recommended):** say `"approve"` in the Claude Code chat.

**Agent CLI:** say `"approve"` inside the active session, or `/review-spec` → approve.

**Frontend UI:** click the green **Approve — Start Engineering ▶** button.

**REST API:**
```bash
curl -X POST http://localhost:8000/approve-spec \
  -H "Content-Type: application/json" \
  -d '{"job_id": "f3a8b21c", "decision": "approve"}'
```

**What you see:**

```
[human_gate] approved — resuming
[Engineer] running...
[Engineer] ✓ done  (22.4 s)
    wrote  projects/hello_django/manage.py
    wrote  projects/hello_django/hello_django/settings.py
    wrote  projects/hello_django/hello_django/urls.py
    wrote  projects/hello_django/hello/views.py
    wrote  projects/hello_django/hello/urls.py
    wrote  projects/hello_django/hello/apps.py

[QA] running...
```

**How to verify Engineer is done:**  
Check that files exist:

```bash
ls projects/hello_django/
# Expected: manage.py  hello_django/  hello/
```

Check via API — `artifact_paths` is populated:

```bash
curl http://localhost:8000/status/f3a8b21c | python -m json.tool
# Look for: "artifact_paths": { "manage.py": "projects/hello_django/manage.py", ... }
```

**How Engineer maps to the flow:**  
`human_gate` node calls LangGraph's `interrupt()` and then returns when `Command(resume="approve")` arrives. Fixed edge routes to `engineer`. Engineer writes files, calls `parse_submit()` → writes `artifact_paths`. Fixed edge routes to `qa`.

---

### Step 4 — QA validates the output

QA runs automatically after Engineer. It does not need your input.

**What QA checks** (per acceptance criteria from the spec):

| Check | Command QA runs | Pass condition |
|---|---|---|
| Django system check | `python manage.py check` | Exit code 0 |
| View returns 200 | Django test client `GET /` | Status 200, body `Hello, World!` |
| File structure | `os.path.exists(...)` | `manage.py`, `views.py`, `urls.py` present |

**Possible outcomes:**

```
[QA] ✓ pass — all checks passed
    status: done
```

or (if Engineer made a mistake):

```
[QA] ✗ fail-minor
    D1  missing 404 handler     views.py:12
    → routing back to Engineer (iteration 1/3)
```

**How to verify QA is done:**  
`test_report` field is populated:

```bash
curl http://localhost:8000/status/f3a8b21c | python -m json.tool
```

```json
"test_report": {
  "status": "pass",
  "summary": "All 3 checks passed",
  "passed": ["django_check", "hello_view_200", "file_structure"],
  "failed": [],
  "defects": []
}
```

**How QA maps to the flow:**  
`qa` node calls `parse_submit()` → writes `test_report`, increments `iteration` on fail. `conditional_edges` calls `route_qa()`:

```python
# route_qa logic (deterministic Python, no LLM):
if report["status"] == "pass":          → "done"
if report["status"] == "fail-minor":
    if iteration >= 3:                  → "failed"
    else:                               → "engineer"   # retry
if report["status"] == "fail-major":
    if qa_analyser_iteration >= 2:      → "failed"
    else:                               → "analyser"   # re-spec
```

---

### Step 5 — Collect your output

When status is `"done"`:

```bash
# Run the Django dev server to verify manually
cd projects/hello_django
pip install django
python manage.py runserver
# → open http://127.0.0.1:8000/ in browser
# → should show: Hello, World!
```

Check the final pipeline status:

```bash
curl http://localhost:8000/status/f3a8b21c | python -m json.tool
```

```json
{
  "job_id": "f3a8b21c",
  "status": "done",
  "current_node": null,
  "tasks": [ ... ],
  "spec": { ... },
  "artifact_paths": {
    "manage.py":                      "projects/hello_django/manage.py",
    "hello_django/settings.py":       "projects/hello_django/hello_django/settings.py",
    "hello_django/urls.py":           "projects/hello_django/hello_django/urls.py",
    "hello/views.py":                 "projects/hello_django/hello/views.py",
    "hello/urls.py":                  "projects/hello_django/hello/urls.py",
    "hello/apps.py":                  "projects/hello_django/hello/apps.py"
  },
  "test_report": {
    "status": "pass",
    "summary": "All checks passed",
    "passed": ["django_check", "hello_view_200", "file_structure"],
    "failed": [],
    "defects": []
  },
  "iteration": 0,
  "qa_analyser_iteration": 0
}
```

---

### Full flow summary — one table

| Step | Agent / Gate | What happens | How to verify | `ProjectContext` field updated |
|---|---|---|---|---|
| 1 | **PM** | Breaks requirement into 3 tasks | `tasks` list has 3 items with `status=pending` | `tasks` |
| 2 | **Analyser** | Writes technical spec (components, API contracts, risks, acceptance criteria) | `spec` field is non-null | `spec` |
| 3 | **Human Gate** | Pipeline pauses — YOU review the spec | API status = `waiting_approval` | _(no change)_ |
| 4 | **[You approve]** | Pipeline resumes from checkpoint | API status returns to `running` | _(no change)_ |
| 5 | **Engineer** | Writes all Django files to `projects/hello_django/` | Files exist on disk, `artifact_paths` populated | `artifact_paths` |
| 6 | **QA** | Runs `manage.py check`, tests view, checks file structure | `test_report.status = "pass"` | `test_report` |
| 7 | **Done** | `handle_done` sets final status | API status = `done` | `status` |

---

### What to do if the pipeline fails

```bash
# See which step failed and why
curl http://localhost:8000/status/f3a8b21c | python -m json.tool

# Key fields to read:
#   "status"       → "failed"
#   "iteration"    → how many Engineer retries happened
#   "test_report"  → which checks failed and why
#   "history"      → full agent event log with timestamps
```

Common fix: add more detail to the prompt and start a new run:

```bash
python -m orchestrator.runner \
  "Build a minimal Django 'Hello World' app under projects/hello_django/. \
   Use Django 4.2. Create a hello app with views.py, urls.py, apps.py. \
   Wire the root URL to hello.views.index which returns HttpResponse('Hello, World!'). \
   Include requirements.txt listing django==4.2."
```
