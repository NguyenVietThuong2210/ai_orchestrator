# PLAN — AI Orchestrator Implementation

> Cập nhật: 2026-05-09 | Mode B first (claude CLI, no API key)

---

## Checklist

### Layer 0 — Foundation (đã hoàn thành)
- [x] `orchestrator/context.py` — ProjectContext TypedDict, Task, TechnicalSpec, TestReport, AgentEvent
- [x] `orchestrator/backends/base.py` — BaseBackend abstract class
- [x] `orchestrator/backends/claude_code_backend.py` — Mode B: `claude -p` subprocess
- [x] `orchestrator/backends/api_backend.py` — Mode A: placeholder
- [x] `orchestrator/backends/__init__.py` — factory `get_backend()`
- [x] `.env.example` — tất cả ENV vars (Mode A + Mode B models)

### Layer 1 — Orchestration Core
- [x] `orchestrator/__init__.py`
- [x] `orchestrator/graph.py` — LangGraph StateGraph, human_gate, route_qa, compile
- [x] `orchestrator/runner.py` — invoke / resume pipeline, stream events

### Layer 2 — Agents
- [x] `agents/__init__.py`
- [x] `agents/base.py` — BaseAgent: system_prompt, build_prompt, parse_submit
- [x] `agents/pm.py` — PM: task breakdown
- [x] `agents/analyser.py` — Analyser: technical spec
- [x] `agents/engineer.py` — Engineer: code implementation
- [x] `agents/qa.py` — QA: test report

### Layer 3 — Tools
- [x] `tools/__init__.py`
- [x] `tools/definitions.py` — JSON schema tool definitions per agent

### Layer 4 — API
- [x] `api/__init__.py`
- [x] `api/schemas.py` — Pydantic I/O models
- [x] `api/routes.py` — /run, /status, /stream (SSE), /approve, /cancel
- [x] `api/main.py` — FastAPI app + lifespan

### Layer 5 — MCP Server
- [x] `mcp_server/__init__.py`
- [x] `mcp_server/server.py` — FastMCP: tools + resources + prompts

### Layer 6 — Config & Tests
- [x] `pyproject.toml` — dependencies, scripts
- [x] `tests/__init__.py`
- [x] `tests/test_context.py` — TypedDict validation
- [x] `tests/test_backends.py` — ClaudeCodeBackend mock (no subprocess)
- [x] `tests/test_graph.py` — graph routing + agent parse_submit

### Layer 7 — React Frontend (Vite + TypeScript + Tailwind)
- [x] `frontend/package.json` — Vite 5, React 18, TypeScript, Tailwind CSS v3
- [x] `frontend/vite.config.ts` — dev proxy `/api` → FastAPI :8000
- [x] `frontend/tsconfig.json` — strict TypeScript
- [x] `frontend/tailwind.config.js` + `postcss.config.js`
- [x] `frontend/index.html`
- [x] `frontend/src/main.tsx`
- [x] `frontend/src/index.css` — Tailwind directives
- [x] `frontend/src/types/index.ts` — mirrors backend Pydantic schemas
- [x] `frontend/src/api/client.ts` — typed fetch wrappers for all routes
- [x] `frontend/src/hooks/useSSE.ts` — EventSource hook with auto-reconnect
- [x] `frontend/src/hooks/usePipeline.ts` — pipeline state machine + polling
- [x] `frontend/src/components/StatusBadge.tsx`
- [x] `frontend/src/components/PipelineForm.tsx` — requirement textarea + Run button
- [x] `frontend/src/components/AgentTimeline.tsx` — real-time SSE event log
- [x] `frontend/src/components/SpecReview.tsx` — spec viewer + Approve / Reject
- [x] `frontend/src/components/ArtifactList.tsx` — engineer output file list
- [x] `frontend/src/components/TestReport.tsx` — QA pass/fail report
- [x] `frontend/src/App.tsx` — sidebar layout, state-driven main panel
- [x] `api/main.py` — mount `frontend/dist` as StaticFiles, SPA fallback

---

## Build Order (dependency graph)

```
context.py
    │
    ├── backends/base.py
    │       ├── backends/claude_code_backend.py ✅
    │       └── backends/api_backend.py ✅
    │
    ├── tools/definitions.py
    │
    ├── agents/base.py
    │       ├── agents/pm.py
    │       ├── agents/analyser.py
    │       ├── agents/engineer.py
    │       └── agents/qa.py
    │
    └── orchestrator/graph.py (wires backends + agents into LangGraph)
            │
            ├── orchestrator/runner.py
            │
            ├── api/routes.py → api/main.py
            │
            └── mcp_server/server.py
```

---

## Key Decisions

| Decision | Choice | Reason |
|---|---|---|
| Mode B implementation | `claude -p` subprocess | No API key, Pro subscription auth |
| Submit protocol | `<submit>...</submit>` JSON block | Works with plain text output from claude CLI |
| Artifact storage | `ARTIFACT_DIR` (filesystem) | claude Engineer writes files natively when cwd=ARTIFACT_DIR |
| Human Gate | `interrupt_before=["human_gate"]` + `Command(resume=)` | LangGraph native, no custom code |
| FAILED state | Separate terminal node | Distinguish từ DONE trong API, UI, Langfuse |
| Mode B Analyser model | Sonnet 4.6 (không có Opus) | Opus cần API key |

---

## Run Commands (after implementation)

```bash
# Setup
cp .env.example .env
pip install -e ".[dev]"
mkdir -p data artifacts

# Mode B — run pipeline (cần Claude Code session mở)
python -m orchestrator.runner "Build a REST API for a todo app"

# API backend
uvicorn api.main:app --reload

# MCP server
python mcp_server/server.py

# Tests
pytest -v

# Frontend — development
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxied to API :8000)

# Frontend — production build (served by FastAPI)
npm run build      # outputs to frontend/dist/
cd ..
uvicorn api.main:app --reload   # serves UI at http://localhost:8000
```
