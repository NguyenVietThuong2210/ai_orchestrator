# Research: AI Agent Frameworks & Repos

> Ngày research: 2026-05-09

---

## Tổng quan thị trường (2025-2026)

| Framework | Language | Pattern chính | Stars/Adoption | Tương thích Claude |
|---|---|---|---|---|
| **CrewAI** | Python | Role-based DSL | 47,800+ ⭐, 2B agent runs/tháng | ✅ Tốt (hỗ trợ MCP) |
| **LangGraph** | Python | Graph/State Machine | Top 3 framework | ✅ Tốt (native LangChain) |
| **Anthropic Agent SDK** | Python/TS | Embedded agent loop | Official Anthropic | ✅✅ Native hoàn toàn |
| **Pydantic AI** | Python | Type-safe agents | Emerging, từ team Pydantic | ✅ Native Anthropic integration |
| **AutoGen** (Microsoft) | Python | Conversation-driven | Đang merge vào Microsoft Agent Framework | ⚠️ Microsoft-centric |
| **Semantic Kernel** | C#/Python | Skill orchestration | 27,770 ⭐ | ⚠️ Microsoft-centric |
| **LlamaIndex Workflows** | Python | Event-driven | Tốt, từ LlamaIndex community | ✅ Hỗ trợ Claude |

### Tin tức quan trọng (2025-2026)
- Microsoft **merge AutoGen + Semantic Kernel** → Microsoft Agent Framework v1.0 (GA Q1 2026)
- **MCP được adopt** bởi OpenAI (tháng 3/2025), Google DeepMind (tháng 4/2025) → MCP đang trở thành chuẩn ngành
- CrewAI đang **phát triển nhanh nhất** trong nhóm open-source agent frameworks

---

## So sánh chi tiết 3 lựa chọn phù hợp nhất

### CrewAI — Khuyến nghị cho MVP nhanh

```
✅ Pros:
- Concept PM/Analyst/Engineer/QA là built-in (role-based native)
- DSL đơn giản, ít boilerplate nhất
- Enterprise customers: PwC, IBM, NVIDIA, Capgemini
- Hỗ trợ MCP, parallel task execution
- 150+ enterprise customers, 450M agents/month

❌ Cons:
- Ít control hơn so với LangGraph
- Not Anthropic-native (nhưng support tốt)
- Khó customize deep behavior

Best for: MVP trong 1-2 tuần, team nhỏ, prototype nhanh
```

### LangGraph — Khuyến nghị cho Production Enterprise

```
✅ Pros:
- Graph-based: hỗ trợ cycles, conditional routing, loops
- LangSmith: visual debugging, step-through, state inspection, replay
- State persistence và checkpointing built-in
- Fault tolerance, durable execution
- Có thể dùng Anthropic SDK bên trong mỗi node

❌ Cons:
- Learning curve cao hơn CrewAI
- Setup phức tạp hơn
- Graph explosion nếu không thiết kế cẩn thận

Best for: Production, complex feedback loops, cần observability mạnh
```

### Anthropic Agent SDK — Khuyến nghị nếu all-in Claude

```
✅ Pros:
- Native hoàn toàn với Claude models
- MCP native, subagents built-in
- Lifecycle hooks, streaming built-in
- Official Anthropic support

❌ Cons:
- Vendor lock-in với Anthropic
- Ít ecosystem hơn LangGraph/CrewAI
- Không có visual debugging như LangSmith

Best for: All-in Claude, muốn tối ưu prompt caching, MCP integration
```

---

## Nguồn
- [CrewAI vs LangGraph vs AutoGen — JetThoughts](https://jetthoughts.com/blog/autogen-crewai-langgraph-ai-agent-frameworks-2025/)
- [Top AI Agent Frameworks 2026 — Turing](https://www.turing.com/resources/ai-agent-frameworks)
- [Open-Source AI Agent Framework Comparison — Langfuse](https://langfuse.com/blog/2025-03-19-ai-agent-comparison)
