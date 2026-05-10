# Research: Cline — "OpenClaw"

> Ngày research: 2026-05-09
> Note: "OpenClaw" mà bạn nghe chính là Cline (tên cũ: Claude Dev)

---

## Cline là gì?

**Cline** (tên cũ: **Claude Dev**) — VS Code extension open-source, autonomous AI coding agent với human-in-the-loop approval.

| | |
|---|---|
| **GitHub** | github.com/cline/cline |
| **Stars** | 61,500+ |
| **License** | Apache 2.0 (miễn phí hoàn toàn) |
| **VS Code installs** | 5M+ |
| **Tên cũ** | Claude Dev (VS Code extension ID: saoudrizwan.claude-dev) |

---

## Cline vs Claude Code

| | **Claude Code** | **Cline** |
|---|---|---|
| **Nhà phát triển** | Anthropic (chính thức) | Community open-source |
| **Chi phí** | Pro subscription ($20/tháng) | Free (Apache 2.0) |
| **LLM support** | Claude only | 30+ providers (Claude, GPT, Gemini, local LLM...) |
| **MCP support** | ✅ Native | ✅ Native |
| **Human approval** | ✅ Configurable | ✅ Mỗi bước |
| **Local model (Ollama)** | ❌ | ✅ (zero cost option) |
| **Phù hợp** | All-in Claude, Pro subscription | Multi-provider, open-source stack |

---

## Core capabilities

| Capability | Mô tả |
|---|---|
| **File operations** | Create, edit files với diff preview |
| **Terminal** | Execute commands, watch output |
| **Browser** | Drive browser qua Puppeteer (Claude's Computer Use) |
| **MCP tools** | Call bất kỳ MCP server nào |
| **Context** | `@url`, `@file`, `@folder`, `@problems` |
| **Checkpoint** | Rollback về state trước |

---

## MCP Integration (quan trọng nhất)

Cline **hỗ trợ MCP native** → có thể dùng với custom MCP Server của AI Orchestrator:

```
Cline (VS Code)
    ↓ MCP Protocol
Custom MCP Server (AI Orchestrator)
    ↓ HTTP
FastAPI Backend
```

**Thực tế:** Cline hoạt động như một alternative client cho VS Code integration — thay thế hoặc bổ sung Claude Code, cùng dùng một MCP Server.

### Ưu điểm khi dùng Cline với Orchestrator
- Hỗ trợ local LLM (Ollama) → agents chạy free hoàn toàn nếu có GPU
- Multi-provider → không bị lock-in vào Anthropic nếu muốn
- Open-source → có thể fork và customize
- Cùng MCP Server → không cần thay đổi backend

---

## Providers Cline hỗ trợ (30+)

| Category | Providers |
|---|---|
| **Cloud** | Anthropic, OpenAI, Google Gemini, AWS Bedrock, Azure, GCP Vertex |
| **Fast inference** | Groq, Cerebras |
| **Aggregator** | OpenRouter (100+ models) |
| **Local** | LM Studio, Ollama |
| **Any** | OpenAI-compatible API |

---

## Quyết định

- **Primary client:** Claude Code (Anthropic chính thức, tích hợp tốt nhất với Pro subscription)
- **Alternative client:** Cline (nếu muốn open-source hoàn toàn, multi-provider, hoặc local LLM)
- **Cùng MCP Server:** Cả hai đều dùng được cùng một MCP server

---

## Nguồn
- [Cline GitHub](https://github.com/cline/cline)
- [Cline MCP Overview](https://docs.cline.bot/mcp/mcp-overview)
- [Cline Official](https://cline.bot/)
