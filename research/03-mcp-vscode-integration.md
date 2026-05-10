# Research: MCP & VS Code Integration

> Ngày research: 2026-05-09

---

## MCP (Model Context Protocol) là gì?

**Model Context Protocol** — chuẩn mở do Anthropic tạo ra (tháng 11/2024):
- Cho phép LLM app kết nối với tools, data sources, services bên ngoài
- 97M+ monthly SDK downloads
- Đã được OpenAI (3/2025) và Google DeepMind (4/2025) adopt → **đang trở thành chuẩn ngành**
- SDK: Python, TypeScript, C#, Java

---

## 3 Primitive của MCP

| Primitive | Đặc điểm | Ai control | Ví dụ trong AI Orchestrator |
|---|---|---|---|
| **Tools** | Actions có side effect | LLM quyết định khi nào call | `run_pipeline()`, `get_job_status()` |
| **Resources** | Read-only data | Client fetch chủ động | `project_spec`, `test_report`, `agent_logs` |
| **Prompts** | Template instructions | User-controlled (slash commands) | `/build-feature`, `/review-spec` |

---

## Kiến trúc tích hợp

```
VS Code + Claude Code (hoặc Cline)
        ↓  MCP Protocol (stdio hoặc HTTP/SSE)
  MCP Server (Python, FastMCP ~60 lines)
        ↓  HTTP REST calls
  FastAPI Backend (AI Orchestrator)
```

**Kết quả:** Bạn type trong VS Code chat → Claude Code gọi MCP tool → pipeline chạy → output stream về chat real-time.

---

## So sánh 4 cách tích hợp VS Code

| | MCP Server | Claude Code Skills | Webhook/SSE | Agent SDK |
|---|:---:|:---:|:---:|:---:|
| Setup | 🟡 Vừa | 🟢 Đơn giản | 🔴 Phức tạp | 🟡 Vừa |
| VS Code integration | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Reusability | ✅ Cross-client | ❌ Claude only | ✅ | ❌ Embedded |
| Type safety | ✅ Pydantic | 🟡 | ❌ | ✅ |
| Enterprise | ✅ | 🟡 Basic | ✅ | ✅ |
| **Quyết định** | ✅✅ **CHỌN** | Dev/testing | Existing systems | All-in Anthropic |

---

## Cách kiểm tra output khi build BE

| Option | Phù hợp | Pros | Cons |
|---|---|---|---|
| **REST Polling** | Dev, testing | Đơn giản, stateless | Không real-time |
| **SSE Streaming** | Dashboard, CLI | Real-time, một connection HTTP | Cần maintain connection |
| **MCP Bridge** | VS Code integration | Output về thẳng IDE chat | Cần MCP server riêng |
| **Webhook Callback** | Tích hợp hệ thống khác | Decoupled, bất kỳ system nào | Client phải expose public endpoint |

---

## Security Warning

> ⚠️ **Prompt injection là vấn đề số 1 chưa được giải quyết trong MCP ecosystem.**
> MCP server chạy code trực tiếp trên máy user.

**Mitigation:**
- Validate và sanitize tất cả input trước khi forward đến backend
- Whitelist allowed actions per user/session
- Log tất cả MCP tool calls
- Không expose raw shell execution qua MCP

---

## Nguồn
- [MCP Architecture Overview — modelcontextprotocol.io](https://modelcontextprotocol.io/docs/learn/architecture)
- [Build MCP Server with Python — FreeCodeCamp](https://www.freecodecamp.org/news/how-to-build-an-mcp-server-with-python-docker-and-claude-code/)
- [Claude Agent SDK Overview — Anthropic](https://code.claude.com/docs/en/agent-sdk/overview)
- [Connect Claude Code to tools via MCP — Claude Docs](https://code.claude.com/docs/en/mcp)
