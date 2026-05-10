# Research: Frontend UI Repos cho Agent State Tracking

> Ngày research: 2026-05-09

---

## Yêu cầu của UI

| Tính năng | Mô tả |
|---|---|
| **DAG Visualization** | Hiển thị graph PM→Analyser→Engineer→QA dạng node-edge |
| **Real-time State** | Agent đang chạy/done/fail, highlight node hiện tại |
| **Log Streaming** | Output từng agent stream về live (SSE) |
| **Token/Cost Tracking** | Hiển thị token usage và chi phí từng agent |
| **Checkpoint History** | List các pipeline runs, click vào xem chi tiết |
| **Human Gates** | UI để approve/reject spec trước khi Engineer chạy |

---

## So sánh các FE Repos

| Framework | Stars | Stack | Self-hosted | License | Đánh giá |
|---|---|---|---|---|---|
| **Langflow** | 148k | React + ReactFlow + Python | ✅ | MIT | Full platform, có thể embed nhưng opinionated |
| **Flowise** | 52.7k | React/TS + Node.js | ✅ | Apache 2.0 | Lighter, dễ tùy chỉnh hơn Langflow |
| **Dify** | 20k+ | Next.js + Python | ✅ | Open-source | Nặng nhất, full MLOps platform |
| **Rivet** | Active | TypeScript/Electron | ✅ | Open-source | Desktop app, có TS lib để embed |
| **ReactFlow** | Active | React library | ✅ (library) | MIT | **Best for custom DAG UI — CHỌN** |
| **Langfuse UI** | 6M+ SDK installs | Next.js | ✅ | Open-source | **Best observability dashboard — CHỌN** |
| **AgentOps** | N/A | SaaS | ❌ Limited | Commercial | Purpose-built agent monitoring, nhưng SaaS |

---

## Chi tiết các lựa chọn tốt nhất

### Langflow (148k stars)
- React frontend dùng ReactFlow nodes, Python backend
- MIT license, Docker deploy
- Hỗ trợ multi-agent, MCP server deployment
- **Vấn đề:** Là full platform với FSM riêng → có thể conflict với custom Supervisor FSM

### Flowise (52.7k stars)
- React/TypeScript frontend, Node.js backend, monorepo
- Apache 2.0, self-hostable trên AWS/Azure/GCP
- Lightweight hơn Dify, onboarding nhanh hơn
- **Vấn đề:** Tương tự Langflow — opinionated platform

### ReactFlow (library)
- MIT license, dùng bởi Langflow và nhiều tool khác
- Dragging nodes, zooming, panning, DAG layout (Dagre)
- Custom node/edge types → full control UI
- **Lý do chọn:** Library thuần, không conflict với backend logic

### Langfuse (6M+ SDK downloads/tháng)
- Open-source observability platform
- Self-hosted, không vendor lock-in
- Traces, prompt management, evaluation, cost tracking
- **Lý do chọn:** Complement tốt cho ReactFlow — một cái lo visualization, một cái lo monitoring

---

## Khuyến nghị: Custom React + ReactFlow + Langfuse

```
React App (TypeScript)
  ├── ReactFlow          → DAG visualization (pipeline graph)
  ├── SSE EventSource    → Real-time agent log streaming
  ├── Zustand            → Agent state management
  ├── Tailwind CSS       → Styling
  └── Langfuse UI embed  → Traces, cost, latency dashboard
```

### Tại sao không dùng Langflow/Flowise?

| | Langflow / Flowise | Custom React + ReactFlow |
|---|---|---|
| Setup time | Nhanh hơn | Lâu hơn |
| Customize | Hạn chế | Full control |
| Conflict với Supervisor FSM | Có thể | Không |
| Vendor lock-in | Vào platform đó | Không |

---

## Layout dashboard đề xuất

```
┌──────────────────────────────────────────────────────────────┐
│  Job: "Build REST API for auth"       Status: ENGINEERING    │
│  Run #3   Started: 14:32   Cost: $0.09   Iteration: 1/3     │
├─────────────────────────┬────────────────────────────────────┤
│   Pipeline DAG          │   Live Agent Log (SSE)            │
│   (ReactFlow)           │                                   │
│                         │  > Engineer: Reading spec...      │
│  [PM✅]→[Analyser✅]    │  > Writing auth/models.py         │
│    → [Engineer🔄]       │  > Writing auth/routes.py         │
│    → [QA⏳]             │  > Running tests...               │
├─────────────────────────┴────────────────────────────────────┤
│  Human Gate: Spec ready for review      [Approve] [Reject]  │
├──────────────────────────────────────────────────────────────┤
│  Token Usage: PM 1.2k | Analyser 8.4k | Engineer 14.1k     │
│  Cost:        $0.00  |  $0.06         |  $0.04    = $0.10   │
└──────────────────────────────────────────────────────────────┘
```

---

## Nguồn
- [Langflow GitHub](https://github.com/langflow-ai/langflow)
- [Flowise GitHub](https://github.com/FlowiseAI/Flowise)
- [ReactFlow](https://reactflow.dev/)
- [Langfuse](https://langfuse.com)
- [AgentOps](https://www.agentops.ai/)
