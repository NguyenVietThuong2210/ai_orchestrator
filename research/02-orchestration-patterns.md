# Research: Orchestration Patterns

> Ngày research: 2026-05-09

---

## Tổng quan 5 patterns

| Pattern | Độ phức tạp | Linh hoạt | Debug | Enterprise | Phù hợp 4 agents |
|---|:---:|:---:|:---:|:---:|:---:|
| Sequential Pipeline | 🟢 Thấp | 🔴 Thấp | ⭐⭐⭐⭐⭐ | ❌ | 🟡 PoC only |
| DAG/Graph (LangGraph) | 🟡 Vừa | 🟢 Cao | ⭐⭐⭐ | ✅ | ✅ |
| **Supervisor FSM** | 🟡 Vừa | 🟢 Cao | ⭐⭐⭐⭐ | ✅✅ | ✅✅ **CHỌN** |
| Event-Driven | 🔴 Cao | 🟢 Cao | ⭐⭐ | ✅ | 🔴 Overkill |
| Hierarchical | 🔴 Cao | 🟡 | ⭐⭐ | ✅ | 🔴 Overkill |

---

## Pattern A — Sequential Pipeline

```
PM → Analyser → Engineer → QA → Done
```

**Dùng cho:** PoC, demo, prototype đơn giản

```
✅ Pros: Đơn giản, dễ debug, dễ test từng bước
❌ Cons: Không có feedback loops, QA fail thì không quay về Engineer được
❌ Cons: Brittle — 1 agent fail là block toàn pipeline
```

---

## Pattern B — DAG/Graph (LangGraph style)

```
PM ──► Analyser ──► Engineer ──► QA
                         ▲              │ fail
                         └─────────────┘
```

**Dùng cho:** Production với logic phức tạp, cần observability mạnh

```
✅ Pros: Linh hoạt nhất, hỗ trợ cycles/loops, state persistence, visual debugging (LangSmith)
✅ Pros: Conditional routing (QA fail → back to Engineer hoặc Analyser)
❌ Cons: Learning curve cao, graph explosion nếu không thiết kế tốt
```

---

## Pattern C — Supervisor/Orchestrator ⭐ KHUYẾN NGHỊ

```
              ┌─────────────────────────────────────┐
              │      SUPERVISOR (deterministic FSM)  │
              │  - KHÔNG phải LLM                   │
              │  - dict lookup cho state transitions │
              │  - checkpoint sau mỗi bước           │
              └──┬────────┬────────┬────────┬───────┘
                 ↓        ↓        ↓        ↓
               [PM]  [Analyser] [Engineer] [QA]
               (pure functions: context_in → context_out)
```

**Dùng cho:** Enterprise production, cần reliability và audit trail

```
✅ Pros: Control plane tách biệt → dễ test riêng
✅ Pros: Supervisor không tốn token (không phải LLM)
✅ Pros: Deterministic, auditable, rollback được
✅ Pros: Human-in-the-loop gates dễ thêm vào
❌ Cons: Single point of failure ở supervisor (dễ fix hơn LLM-based)
```

**State Machine cụ thể:**

```python
TRANSITIONS = {
    (State.PM_PLANNING,   Status.OK):      State.ANALYSIS,
    (State.ANALYSIS,      Status.OK):      State.ENGINEERING,
    (State.ENGINEERING,   Status.OK):      State.QA_TESTING,
    (State.QA_TESTING,    Status.PASS):    State.DONE,
    (State.QA_TESTING,    Status.FAIL):    State.ENGINEERING,   # minor bugs
    (State.QA_TESTING,    Status.MAJOR):   State.ANALYSIS,      # spec sai
}
```

---

## Pattern D — Event-Driven / Message Bus

**Dùng cho:** Khi scale lên 10+ agents song song (overkill cho 4 agents)

```
✅ Pros: Fully decoupled, async, scale tốt
❌ Cons: Eventual consistency — khó trace "đang ở bước nào"
❌ Cons: Over-engineering cho 4 agents, cần Redis/Kafka infrastructure
```

---

## Pattern E — Hierarchical Multi-Agent

**Dùng cho:** Phase 2, khi mỗi role cần nhiều workers song song

```
✅ Pros: Scale tốt cho team lớn, mirror real org structure
❌ Cons: Latency cao do delegation chain, over-complex ban đầu
```

---

## Nguồn
- [AI Agent Orchestration Patterns — Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
- [Supervisor Architecture for Enterprise AI — Databricks](https://www.databricks.com/blog/multi-agent-supervisor-architecture-orchestrating-enterprise-ai-scale)
- [Multi-Agent Architecture — TrueFoundry](https://www.truefoundry.com/blog/multi-agent-architecture)
