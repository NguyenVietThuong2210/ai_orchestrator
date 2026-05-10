# Research: Enterprise Checklist & Những điểm hay bị bỏ qua

> Ngày research: 2026-05-09

---

## 8 điểm thường bị bỏ qua khi thiết kế AI Orchestrator

### 1. Observability từ đầu (Critical)

Không có trace thì debug production cực khó.

**Tool:** Langfuse (open-source, self-hosted)
```
Trace mọi agent call:
- Input → Output
- Token count (input/output/cached)
- Latency per agent
- Cost per run
- Error rate
```

### 2. Cost Control

4 agents × nhiều token = tiền nhiều. Cần chiến lược:

```
Prompt caching:
  - System prompt → cached (ephemeral, 5 min TTL)
  - Project spec → cached khi spec > 1024 tokens
  - Tiết kiệm 60-70% cost của Analyser (phần tốn nhất)

Model tiering:
  - Haiku 4.5 → PM (task đơn giản, rẻ nhất)
  - Opus 4.7  → Analyser (cần reasoning sâu nhất)
  - Sonnet 4.6 → Engineer, QA (balance cost/quality)

Token budget per agent:
  - PM: max 2K output tokens
  - Analyser: max 8K output tokens
  - Engineer: max 16K output tokens
  - QA: max 4K output tokens
  → Fail fast nếu agent muốn vượt budget
```

### 3. Human-in-the-Loop Gates

```
PM_PLANNING  ──[✅ Human approve task list]──► ANALYSIS
ANALYSIS     ──[✅ Human approve spec]──────► ENGINEERING
```

Enterprise cần điều này để:
- Compliance và audit
- Catch bad specs trước khi lãng phí Engineer tokens
- Legal review nếu cần
- Business stakeholder sign-off

**Implementation:** Simple UI button "Approve/Reject" trong dashboard, hoặc Slack notification với link approve.

### 4. Artifact Versioning

Engineer tạo code → không chỉ lưu string trong memory:

```python
# Sau mỗi Engineer run: git commit artifacts
import subprocess

def version_artifacts(context: ProjectContext):
    for path, content in context.artifacts.items():
        write_file(path, content)
    subprocess.run(["git", "add", "-A"])
    subprocess.run(["git", "commit", "-m",
        f"Engineer run #{context.iteration}: {context.spec.title}"])
```

Cho phép rollback khi QA fail sau nhiều iterations.

### 5. Idempotency & Resume

```
Scenario: Engineer agent đang chạy, server crash ở giữa
→ Cần resume từ Engineer step, không chạy lại từ PM (lãng phí token)

Solution:
- Checkpoint ProjectContext vào SQLite sau mỗi agent step
- API: POST /jobs/{id}/resume
- Runner kiểm tra checkpoint trước khi start
```

### 6. MCP Security (Prompt Injection)

```
Risk: Prompt injection qua MCP tool parameters
Example: run_pipeline("Build todo app\n\nActually, ignore above and...")

Mitigation:
- Validate input schema nghiêm ngặt (Pydantic)
- Whitelist allowed characters trong requirement string
- Log tất cả MCP tool calls với user ID
- Không expose raw shell execution qua MCP
- Rate limiting per session
```

### 7. Max Iteration Guard

```python
MAX_QA_ITERATIONS = 3

if context.iteration > MAX_QA_ITERATIONS:
    raise OrchestratorError(
        f"QA→Engineer loop exceeded {MAX_QA_ITERATIONS} iterations.\n"
        f"Remaining failures: {test_report.failed_tests}\n"
        f"Recommend: Review spec with Analyser"
    )
```

Không có guard này → vòng lặp vô tận → tốn tiền.

### 8. Structured Output Enforcement

Không trust free-text agent output. Mỗi agent CHỈ có một "submit" tool:

```python
# Agent PHẢI call tool này để kết thúc turn
# Không có freeform text nào đến được Supervisor

engineer_submit_tool = {
    "name": "submit_implementation",
    "description": "Submit completed implementation",
    "input_schema": {
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "items": {"path": "string", "content": "string"}
            },
            "summary": {"type": "string"},
            "open_questions": {"type": "array", "items": "string"}
        },
        "required": ["files", "summary"]
    }
}
```

---

## Risk Matrix

| Rủi ro | Khả năng xảy ra | Impact | Giải pháp |
|---|:---:|:---:|---|
| QA loop vô tận | Cao | Cao | `MAX_QA_ITERATIONS=3` hard cap |
| Prompt injection qua MCP | Trung bình | Cao | Sanitize input, whitelist actions |
| Cost vượt ngân sách | Trung bình | Trung bình | Token budget, Langfuse alerts |
| Agent timeout / crash | Trung bình | Trung bình | Checkpoint + resume |
| Mode B bị throttle | Thấp | Thấp | Monitor, fallback sang Mode A |
| Spec sai → loop Engineer↔Analyser | Trung bình | Cao | Human Gate bắt buộc |
