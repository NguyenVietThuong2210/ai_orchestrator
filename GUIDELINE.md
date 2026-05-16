# AI Orchestrator — Usage Guideline

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quick Start — Docker (recommended)](#2-quick-start--docker-recommended)
3. [Local Development Setup](#3-local-development-setup)
4. [Environment Variable Reference](#4-environment-variable-reference)
5. [Running the Pipeline](#5-running-the-pipeline)
   - [Option 1 — MCP Server · VS Code / Claude Code ⭐](#51-option-1--mcp-server--vs-code--claude-code-)
   - [Option 2 — Frontend UI](#52-option-2--frontend-ui)
   - [Option 3 — REST API](#53-option-3--rest-api)
   - [Option 4 — Python CLI](#54-option-4--python-cli)
6. [Human Gate — Approval Flow](#6-human-gate--approval-flow)
7. [Checkpoint & Resume](#7-checkpoint--resume)
8. [Running Tests](#8-running-tests)
9. [Troubleshooting](#9-troubleshooting)
10. [End-to-End Example: Django Hello App](#10-end-to-end-example-django-hello-app)

---

## 1. Prerequisites

| Requirement | Minimum | Notes |
|---|---|---|
| Docker + Docker Compose | 24+ | For the recommended setup |
| Python | 3.11+ | For local dev only |
| Node.js | 18+ | For frontend dev only |
| Claude Code CLI | latest | `npm i -g @anthropic-ai/claude-code` |
| Claude Pro subscription | — | Mode B (default) uses CLI auth |
| PostgreSQL | 16+ | Provided by Docker; or bring your own |

> **Mode A (API key):** Set `AI_BACKEND=api` + `ANTHROPIC_API_KEY`. Claude Code CLI not required.  
> **Mode B (default):** Set `AI_BACKEND=claude_code`. Uses Claude Pro subscription via CLI.

---

## 2. Quick Start — Docker (recommended)

```bash
# 1. Clone and enter the project
cd ai_orchestrator

# 2. Create your env file
cp .env.docker .env
# Edit .env — change POSTGRES_PASSWORD at minimum

# 3. Build and start (Postgres + backend + frontend)
docker-compose up --build

# Frontend + API:  http://localhost:8000
# API docs:        http://localhost:8000/docs
# Postgres:        localhost:5432
```

**To stop:**
```bash
docker-compose down          # stop containers, keep data
docker-compose down -v       # stop + delete Postgres volume
```

**To rebuild after code changes:**
```bash
docker-compose up --build
```

---

## 3. Local Development Setup

### 3.1 Start PostgreSQL

You need a running PostgreSQL instance. Easiest with Docker:

```bash
docker run -d \
  --name orchestrator-pg \
  -e POSTGRES_DB=orchestrator \
  -e POSTGRES_USER=orchestrator \
  -e POSTGRES_PASSWORD=orchestrator \
  -p 5432:5432 \
  postgres:16-alpine
```

Or use an existing local Postgres — just create a database:

```sql
CREATE DATABASE orchestrator;
CREATE USER orchestrator WITH PASSWORD 'orchestrator';
GRANT ALL PRIVILEGES ON DATABASE orchestrator TO orchestrator;
```

### 3.2 Install Python dependencies

```bash
pip install -e ".[dev]"
```

### 3.3 Configure environment

```bash
cp .env.docker .env
```

Edit `.env`:

```dotenv
DATABASE_URL=postgresql://orchestrator:orchestrator@localhost:5432/orchestrator
AI_BACKEND=claude_code
```

### 3.4 Start the backend

```bash
uvicorn api.main:app --reload --port 8000
```

On startup, LangGraph automatically creates its checkpoint tables in Postgres (via `checkpointer.setup()`).

### 3.5 Start the frontend (dev mode with hot reload)

```bash
cd frontend
npm install   # first time only
npm run dev
# → http://localhost:5173  (proxies /api → :8000)
```

### 3.6 Build frontend for production

```bash
cd frontend && npm run build
# FastAPI serves frontend/dist/ at http://localhost:8000
```

---

## 4. Environment Variable Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | **yes** | — | PostgreSQL connection string |
| `AI_BACKEND` | no | `claude_code` | `claude_code` (Mode B) or `api` (Mode A) |
| `ANTHROPIC_API_KEY` | Mode A only | — | Anthropic API key |
| **Mode B models** | | | |
| `PM_MODEL_B` | no | `claude-haiku-4-5-20251001` | PM agent, Mode B |
| `ANALYSER_MODEL_B` | no | `claude-sonnet-4-6` | Analyser, Mode B |
| `ENGINEER_MODEL_B` | no | `claude-sonnet-4-6` | Engineer, Mode B |
| `REVIEWER_MODEL_B` | no | `claude-haiku-4-5-20251001` | Code Reviewer, Mode B |
| `SECURITY_MODEL_B` | no | `claude-sonnet-4-6` | Security scanner, Mode B |
| `QA_MODEL_B` | no | `claude-sonnet-4-6` | QA, Mode B |
| `DEPLOY_MODEL_B` | no | `claude-sonnet-4-6` | Deploy agent, Mode B |
| `RETROSPECTIVE_MODEL_B` | no | `claude-haiku-4-5-20251001` | Retrospective, Mode B |
| **Mode A models** | | | |
| `PM_MODEL` | no | `claude-haiku-4-5-20251001` | PM agent, Mode A |
| `ANALYSER_MODEL` | no | `claude-opus-4-7` | Analyser, Mode A |
| `ENGINEER_MODEL` | no | `claude-sonnet-4-6` | Engineer, Mode A |
| `REVIEWER_MODEL` | no | `claude-haiku-4-5-20251001` | Code Reviewer, Mode A |
| `SECURITY_MODEL` | no | `claude-sonnet-4-6` | Security scanner, Mode A |
| `QA_MODEL` | no | `claude-sonnet-4-6` | QA, Mode A |
| `DEPLOY_MODEL` | no | `claude-sonnet-4-6` | Deploy agent, Mode A |
| `RETROSPECTIVE_MODEL` | no | `claude-haiku-4-5-20251001` | Retrospective, Mode A |
| **Pipeline limits** | | | |
| `MAX_QA_ITERATIONS` | no | `3` | Max Engineer retries before pipeline fails |
| `MAX_QA_ANALYSER_ITERATIONS` | no | `2` | Max Analyser re-spec cycles before pipeline fails |
| `MAX_TOKENS_PER_AGENT` | no | `0` | Token budget per agent turn (0 = disabled) |
| **Paths** | | | |
| `PROJECTS_ROOT` | no | `./projects` | Root for generated code + spec folders |
| **Other** | | | |
| `LOG_LEVEL` | no | `INFO` | `DEBUG` / `INFO` / `WARNING` |
| `CORS_ORIGINS` | no | `http://localhost:5173,http://localhost:8000` | Comma-separated allowed origins |
| `POSTGRES_DB` | Docker only | `orchestrator` | PostgreSQL database name |
| `POSTGRES_USER` | Docker only | `orchestrator` | PostgreSQL user |
| `POSTGRES_PASSWORD` | Docker only | — | PostgreSQL password — **change in production** |

> `DATABASE_URL` is the only hard requirement. The server will refuse to start without it and print a clear error message.

---

## 5. Running the Pipeline

> **Priority order:** MCP → Frontend UI → REST API → Python CLI.

---

### 5.1 Option 1 — MCP Server · VS Code / Claude Code ⭐

The MCP server exposes orchestrator tools directly inside Claude Code. You interact in plain language.

**Step 1 — Start the backend** (Docker or local dev, see §2/§3)

**Step 2 — Register the MCP server** (`.mcp.json` in project root):

```json
{
  "mcpServers": {
    "ai-orchestrator": {
      "command": "python",
      "args": ["mcp_server/server.py"],
      "cwd": "/path/to/ai_orchestrator"
    }
  }
}
```

**Step 3 — Use in Claude Code:**

```
Run the pipeline: build a Django hello-world app in projects/hello_django/
```

Claude calls `run_pipeline` → streams status → pauses at Human Gate → asks you to review → calls `approve_spec` when you say yes.

**Available MCP tools:**

| Tool | When to use |
|---|---|
| `run_pipeline` | Start a new pipeline with a requirement |
| `get_job_status` | Check status + read all agent reports |
| `clarify_job` | Submit answers when status == `waiting_clarification` |
| `approve_spec` | Approve spec when status == `waiting_approval` |
| `cancel_job` | Cancel a running job |

**Available MCP resources:**

| Resource | Contents |
|---|---|
| `project_spec/{job_id}` | Analyser TechnicalSpec |
| `code_review_report/{job_id}` | Reviewer findings |
| `security_report/{job_id}` | bandit + pip-audit results |
| `test_report/{job_id}` | QA defects and pass/fail |
| `deploy_report/{job_id}` | Smoke test result and endpoint |
| `retrospective/{job_id}` | Lessons learned + metrics |
| `agent_logs/{job_id}` | Full event history |

---

### 5.2 Option 2 — Frontend UI

Open `http://localhost:8000` (production) or `http://localhost:5173` (dev).

```
┌─ Header ──────────────────────────────────────────────────────────────────────────────┐
│  🤖 AI Orchestrator  [job-id]  [PM·Clarify·Analyser·Approve·Eng·Review·Sec·QA·Deploy·Retro]  [●] │
├─ Sidebar (w-60) ──┬─ Timeline (w-72) ──┬─ Right Panel (flex-1) ─────────────────────┤
│  Requirement form │  Real-time events  │  Tabs:                                     │
│  Stat tiles       │  Agent cards       │    Tasks · Spec · Code Review · Security   │
│  PM Task board    │  SSE live feed     │    Files · QA · Deploy · Retro             │
│                   │                    │  [Sticky Clarification banner]             │
│                   │                    │  [Sticky Approve banner]                   │
└───────────────────┴────────────────────┴────────────────────────────────────────────┘
```

**Key interactions:**
- Enter requirement → **Run ▶** → watch 10-step progress bar and timeline
- If PM has questions → purple **"Awaiting Clarification"** status → answer in the Clarification banner → **Submit**
- When status hits **"Awaiting Approval"** → right panel auto-switches to Spec tab → click **✓ Approve**
- After each agent completes → timeline card appears; right panel tabs auto-switch
- After Deploy → Retrospective runs automatically; **"Done"** status appears

---

### 5.3 Option 3 — REST API

```bash
# Start a pipeline
curl -X POST http://localhost:8000/run-pipeline \
  -H "Content-Type: application/json" \
  -d '{"requirement": "Build a REST API for a todo app"}'
# → {"job_id": "a1b2c3d4", "status": "started"}

# Poll status
curl http://localhost:8000/status/a1b2c3d4

# Approve spec
curl -X POST http://localhost:8000/approve-spec \
  -H "Content-Type: application/json" \
  -d '{"job_id": "a1b2c3d4", "decision": "approve"}'

# Stream real-time events (SSE)
curl -N http://localhost:8000/stream/a1b2c3d4

# Cancel
curl -X POST http://localhost:8000/cancel/a1b2c3d4
```

Full interactive docs: `http://localhost:8000/docs`

---

### 5.4 Option 4 — Python CLI

Requires `DATABASE_URL` in environment:

```bash
export DATABASE_URL=postgresql://orchestrator:orchestrator@localhost:5432/orchestrator

python -m orchestrator.runner "Build a REST API for a todo app"
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

## 6. Clarification Gate + Human Gate

The pipeline has **two pause points**:

### 6.1 Clarification Gate (optional — only when requirement is ambiguous)

PM flags `needs_clarification = true` and writes `clarification_questions`. The graph pauses before running Analyser.

```
PM → ⏸ PAUSE (clarify here) → Analyser → ...
```

| Interface | How pause appears |
|---|---|
| **MCP / Claude Code** | `get_job_status` returns `"status": "waiting_clarification"` + `clarification_questions[]` |
| **Frontend UI** | Purple **"Awaiting Clarification"** status pill; Clarification banner appears with PM's questions |
| **REST API** | `GET /status/{job_id}` → `"status": "waiting_clarification"`, `"clarification_questions": [...]` |

**Resume after clarifying:**
- **MCP:** `clarify_job(job_id, "answers to questions")`
- **Frontend UI:** type answers in textarea → click **Submit Answers**
- **REST API:** `POST /clarify/{job_id}` with `{"clarification_context": "..."}`

### 6.2 Human Gate (always — spec approval)

The pipeline **always pauses** after the Analyser writes the technical spec. No code is written until you approve.

```
... → Analyser → ⏸ PAUSE (review here) → Engineer → Reviewer → Security → QA → Deploy → Retrospective → DONE
```

| Interface | How pause appears |
|---|---|
| **MCP / Claude Code** | `get_job_status` returns `"status": "waiting_approval"` + full `spec` |
| **Frontend UI** | Amber **"Awaiting Approval"** status; right panel switches to Spec tab; sticky Approve banner appears |
| **REST API** | `GET /status/{job_id}` → `"status": "waiting_approval"` + `"spec": {...}` |

**Approve:**
- **MCP:** `approve_spec(job_id)` or `approve_spec(job_id, "approve")`
- **Frontend UI:** click **✓ Approve — Start Engineering**
- **REST API:** `POST /approve-spec` with `{"job_id": "...", "decision": "approve"}`

**Reject:**
- **MCP:** `approve_spec(job_id, "reject")`
- **Frontend UI:** click **✗ Reject**
- **REST API:** `POST /approve-spec` with `{"job_id": "...", "decision": "reject"}`

> Both checkpoint states are saved in PostgreSQL. You can close everything and come back later.

---

## 7. Checkpoint & Resume

Every agent step is checkpointed to PostgreSQL automatically. If the server restarts mid-pipeline, the job can be resumed from the exact same node.

**Resume via MCP:**
```
Resume job a1b2c3d4
```

**Resume via REST API:**
```bash
curl -X POST http://localhost:8000/run-pipeline \
  -H "Content-Type: application/json" \
  -d '{"requirement": "", "job_id": "a1b2c3d4"}'
```

**Resume via Python CLI:**
```bash
python -m orchestrator.runner "" --job-id a1b2c3d4
```

> Checkpoint tables (`checkpoints`, `checkpoint_writes`, `checkpoint_migrations`) are created automatically by LangGraph on first startup. Never delete them while jobs are running.

---

## 8. Running Tests

```bash
# All tests
pytest

# Verbose
pytest -v

# Specific file
pytest tests/test_backends.py -v
pytest tests/test_graph.py -v

# Lint
ruff check .
ruff format --check .
```

> Tests are fully offline — no subprocess, no API call, no database required.

---

## 9. Troubleshooting

### `RuntimeError: DATABASE_URL is not set`

The server requires a PostgreSQL connection string.

```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/orchestrator
# or add it to .env
```

---

### `connection refused` to PostgreSQL

Postgres is not running or unreachable.

```bash
# Check Docker container
docker ps | grep postgres
docker logs orchestrator-pg

# Or start via docker-compose
docker-compose up postgres
```

---

### `No <submit> block found in output`

The claude subprocess response did not include the required `<submit>...</submit>` JSON block.

**Cause:** Model ran out of context, was interrupted, or misunderstood the prompt.

**Fix:**
- Re-run (checkpoint resumes from the failed node)
- Upgrade model: `ANALYSER_MODEL_B=claude-opus-4-7`
- Set `LOG_LEVEL=DEBUG` to see raw claude output

---

### `json.JSONDecodeError` inside `<submit>` block

Model produced malformed JSON in the submit block.

**Fix:** Retry or upgrade model. `LOG_LEVEL=DEBUG` shows raw output.

---

### `claude.cmd: command not found` (Windows)

Claude Code CLI is not installed or not on PATH.

```bash
npm i -g @anthropic-ai/claude-code
claude --version
```

> On Windows, the CLI is `claude.cmd`. The backend calls it via `claude.cmd` automatically — no manual change needed.

---

### `Cannot be launched inside another Claude Code session`

The `CLAUDECODE` environment variable is set in the parent process, blocking nested `claude` calls.

**Fix:** The backend strips `CLAUDECODE` from subprocess env automatically. If you see this error, check that you're running the latest `claude_code_backend.py`.

---

### Pipeline stuck at `waiting_clarification`

The PM has ambiguous requirements and is waiting for your answers.

- **Frontend UI:** type answers in the purple Clarification banner → click **Submit Answers**
- **REST API:** `POST /clarify/{job_id}` with `{"clarification_context": "your answers"}`
- **MCP:** call `clarify_job(job_id, "your answers to the questions")`

---

### Pipeline stuck at `waiting_approval`

The Human Gate is paused, waiting for your spec approval.

- **Frontend UI:** click the **✓ Approve** button in the sticky amber banner
- **REST API:** `POST /approve-spec` with `{"job_id": "...", "decision": "approve"}`
- **MCP:** `approve_spec(job_id)` in Claude Code chat

---

### `iteration` keeps hitting `MAX_QA_ITERATIONS`

Engineer and QA are in a fail loop.

1. `GET /status/{job_id}` → check `test_report.defects` for recurring issues
2. Increase `MAX_QA_ITERATIONS` temporarily
3. Add more detail to the original requirement
4. Upgrade `ENGINEER_MODEL_B` to a more capable model

---

## Pipeline Status Reference

| Status | Meaning | UI color |
|---|---|---|
| `idle` | No active job | Gray |
| `starting` | Submission accepted, PM about to run | Blue |
| `running` | An agent is actively executing | Blue (pulsing) |
| `waiting_clarification` | PM has questions — awaiting user answers | Purple (pulsing) |
| `waiting_approval` | Paused at Human Gate — awaiting spec approval | Amber (pulsing) |
| `done` | All 8 agents completed; artifacts + retrospective available | Green |
| `failed` | Max iterations exceeded, security/deploy failed, or unrecoverable error | Red |

---

## 10. End-to-End Example: Django Hello App

**Goal:** Build a minimal Django "Hello World" app under `projects/hello_django/`.

### Pipeline flow

```
Your prompt
    ↓
[PM Agent]          → tasks + Definition of Done (may pause for clarification)
    ↓
[Analyser Agent]    → technical spec
    ↓
[Human Gate]        ← YOU review + approve here
    ↓
[Engineer Agent]    → writes all files into projects/hello_django/
    ↓
[Reviewer Agent]    → code quality check (text-only)
    ↓
[Security Agent]    → bandit + pip-audit scan
    ↓
[QA Agent]          → runs django check, tests view, file structure
    ↓
[Deploy Agent]      → installs deps, starts on :9000, smoke-tests curl
    ↓
[Retrospective]     → lessons learned document
    ↓
    ├── deploy pass → DONE ✓
    └── any fail   → Retrospective → FAILED (with lessons)
```

### Step 1 — Start the pipeline

**MCP (recommended):**
```
Run the AI orchestrator pipeline:
Build a minimal Django "Hello World" web app.
Store all files under projects/hello_django/.
The app must have one view at / that returns "Hello, World!"
and must be runnable with: python manage.py runserver
```

**Python CLI:**
```bash
python -m orchestrator.runner \
  "Build a minimal Django Hello World app. \
   Store all files under projects/hello_django/. \
   One view at / returning Hello, World! \
   Runnable with python manage.py runserver"
```

**What you see:**
```
[PM]       ✓  3 tasks created  (1.4s)
[Analyser] ✓  spec ready       (8.2s)
⏸  Human Gate — spec ready for review — job_id: f3a8b21c
```

### Step 2 — Review and approve the spec

Expected spec (abbreviated):

```json
{
  "overview": "Minimal Django app with a single / endpoint returning Hello, World!",
  "components": [
    {"name": "hello_django/", "description": "Django project root"},
    {"name": "hello/views.py", "description": "View returning HttpResponse"},
    {"name": "hello/urls.py", "description": "URL conf for /"}
  ],
  "api_contracts": [
    {"method": "GET", "path": "/", "response": "200 Hello, World!"}
  ],
  "acceptance_criteria": [
    "GET / returns HTTP 200 with body Hello, World!",
    "python manage.py check exits 0"
  ]
}
```

Approve → Engineering starts automatically.

### Step 3 — Engineer writes the files

```
[Engineer] ✓ done (22.4s)
  wrote  projects/hello_django/manage.py
  wrote  projects/hello_django/hello_django/settings.py
  wrote  projects/hello_django/hello_django/urls.py
  wrote  projects/hello_django/hello/views.py
  wrote  projects/hello_django/hello/urls.py
```

### Step 4 — QA validates

| Check | Command | Pass condition |
|---|---|---|
| Django system check | `python manage.py check` | Exit 0 |
| View returns 200 | Django test client `GET /` | Status 200, body `Hello, World!` |
| File structure | `os.path.exists(...)` | `manage.py`, `views.py`, `urls.py` present |

### Step 5 — Collect output

```bash
cd projects/hello_django
pip install django
python manage.py runserver
# → http://127.0.0.1:8000/ → Hello, World!
```

Final API status:

```json
{
  "status": "done",
  "artifact_paths": {
    "manage.py": "projects/hello_django/manage.py",
    "hello/views.py": "projects/hello_django/hello/views.py"
  },
  "test_report": {
    "status": "pass",
    "passed": ["django_check", "hello_view_200", "file_structure"],
    "defects": []
  }
}
```

### Step → Agent mapping

| Step | Agent | `ProjectContext` field updated |
|---|---|---|
| 1 | **PM** | `tasks`, `definition_of_done`, `needs_clarification` |
| 2 | **Analyser** | `spec` |
| 3 | **Human Gate** | _(no change — checkpoint saved)_ |
| 4 | **Engineer** | `artifact_paths`, `project_dir` |
| 5 | **Reviewer** | `code_review_report` |
| 6 | **Security** | `security_report` |
| 7 | **QA** | `test_report` |
| 8 | **Deploy** | `deploy_report` |
| 9 | **Retrospective** | `retrospective` |
| 10 | **Done/Failed** | `status = "done"` or `"failed"` |
