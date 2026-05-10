# Research: Paperclip — Multi-Agent Orchestration Framework

> Ngày research: 2026-05-09

---

## Paperclip là gì?

**Paperclip** — framework open-source để orchestrate nhiều AI agents thành một "tổ chức ảo" (zero-human company), với org chart, budget, governance, và heartbeat scheduling.

| | |
|---|---|
| **GitHub** | github.com/paperclipai/paperclip |
| **Stars** | 63,700+ (ra mắt 3/2026, tăng trưởng cực nhanh) |
| **License** | MIT |
| **Stack** | Node.js 20 + TypeScript + React + PostgreSQL |
| **Self-hosted** | ✅ Fully local, embedded PostgreSQL |
| **Launch** | `npx paperclipai onboard --yes` |

---

## Core Concept: Heartbeat Pattern

**Vấn đề:** Agents accumulate conversation history → tốn context/token, dễ bị "drift" theo thời gian.

**Giải pháp của Paperclip:**

```
Mỗi agent không "nhớ" lịch sử conversation.

Thay vào đó:
1. Agent "thức dậy" theo schedule (heartbeat)
2. Nhận context packet mới (memory state + open tasks + recent inputs)
3. Xử lý, ghi output vào shared storage
4. "Ngủ" lại

Agent tiếp theo "thức dậy" → đọc output của agent trước từ shared storage
→ Stateless agents, không bị context drift
```

---

## Tính năng nổi bật

| Tính năng | Mô tả |
|---|---|
| **Org Chart** | Định nghĩa hierarchy agents (CEO → Leads → Workers) |
| **Budget Management** | Per-agent spending limits, auto-throttle khi vượt budget |
| **Goal Alignment** | Company objectives cascade xuống từng agent |
| **Heartbeat Scheduling** | Agents wake up theo interval, nhận fresh context |
| **Audit Trails** | Full log mọi agent action |
| **Governance** | Approval workflows, identity/access management |
| **Company Portability** | Export/import company configurations |
| **Plugin System** | Extensible qua plugins |

---

## So sánh với Supervisor FSM Pattern (của AI Orchestrator)

| | **Paperclip Heartbeat** | **Supervisor FSM (của chúng ta)** |
|---|---|---|
| **Trigger** | Schedule-based (time interval) | Event-based (khi agent done) |
| **State** | Injected qua context packet | ProjectContext object (SQLite) |
| **Cost control** | Per-agent budget limits built-in | Manual (MAX_ITERATIONS guard) |
| **UI** | Built-in React UI | Tự build (ReactFlow) |
| **Latency** | Có delay do schedule | Real-time (ngay khi agent done) |
| **Stack** | Node.js + TypeScript | Python + FastAPI |
| **Phù hợp** | Long-running async, autonomous tasks | Real-time pipeline, streaming output |

---

## Use case "AI Engineering Company" với Paperclip

```
PM Agent       → viết requirements
Architect      → design system
Senior Engineer → implement core logic
Junior Engineer → viết tests
DevOps Agent   → deploy và monitor
CFO Agent      → track costs và budgets (built-in!)
```

Paperclip orchestrate timing, communication, và budget constraints của tất cả agents trên.

---

## Providers hỗ trợ

- Claude, Codex, OpenCode, Cursor (built-in)
- 100+ models qua OpenRouter

---

## Đánh giá cho AI Orchestrator

**Pros:**
- ✅ Giải quyết đúng bài toán multi-agent coordination
- ✅ Built-in cost management (không cần tự implement)
- ✅ Built-in React UI
- ✅ Heartbeat pattern phù hợp cho autonomous long-running tasks
- ✅ MIT license, fully self-hosted

**Cons:**
- ❌ Node.js/TypeScript stack → không match với Python backend plan
- ❌ Heartbeat model có thể delay so với real-time pipeline
- ❌ Khá mới (3/2026), ecosystem còn đang build
- ❌ Company/org abstraction có thể overkill cho 4 agents

**Quyết định:** Theo dõi — không dùng ngay (stack mismatch). Nếu sau này muốn chuyển sang Node.js hoặc cần built-in budget management thì xem xét lại.

---

## Nguồn
- [Paperclip GitHub](https://github.com/paperclipai/paperclip)
- [Paperclip Official](https://paperclip.ing/)
- [What Is Paperclip? Zero-Human AI Company Framework](https://www.mindstudio.ai/blog/what-is-paperclip-zero-human-ai-company-framework)
- [Heartbeat Pattern Explained](https://www.mindstudio.ai/blog/what-is-heartbeat-pattern-paperclip-ai-agents)
