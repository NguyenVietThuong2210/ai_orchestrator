# Research: Dual-Mode — API vs Claude Code với ENV Flag

> Ngày research: 2026-05-09

---

## Vấn đề

Cần một codebase support cả 2 modes:
- **Mode B (default):** Claude Code sub-agents — FREE, dùng Pro subscription
- **Mode A:** Anthropic API direct calls — trả tiền theo token, standalone service

---

## Giải pháp: Strategy Pattern + ENV Flag

```bash
AI_BACKEND=claude_code   # default — dùng Claude Code session
AI_BACKEND=api           # dùng Anthropic API — cần API key + credit
```

**Cách switch:** Chỉ đổi ENV var trong `.env`, restart service. Không cần thay đổi code Supervisor, MCP Server, hay UI.

---

## Kiến trúc code (Strategy Pattern)

```python
# agents/base.py — Interface chung cho cả 2 modes
class BaseAgentRunner(ABC):
    @abstractmethod
    async def invoke(self, context: ProjectContext) -> AgentResult:
        ...

# agents/api_runner.py — Mode A: Gọi Anthropic API trực tiếp
class APIAgentRunner(BaseAgentRunner):
    def __init__(self, model: str):
        self.client = anthropic.Anthropic()
        self.model = model

    async def invoke(self, context: ProjectContext) -> AgentResult:
        response = self.client.messages.create(
            model=self.model,
            system=[{"type": "text", "text": system_prompt,
                     "cache_control": {"type": "ephemeral"}}],
            messages=build_messages(context),
            tools=self.tools,
        )
        return parse_result(response)

# agents/claude_code_runner.py — Mode B: Spawn Claude Code sub-agent
class ClaudeCodeAgentRunner(BaseAgentRunner):
    async def invoke(self, context: ProjectContext) -> AgentResult:
        result = await spawn_subagent(prompt=build_prompt(context))
        return parse_result(result)

# agents/factory.py — ENV flag router
AI_BACKEND = os.getenv("AI_BACKEND", "claude_code")
MODEL_MAP = {
    "pm":       "claude-haiku-4-5-20251001",
    "analyser": "claude-opus-4-7",
    "engineer": "claude-sonnet-4-6",
    "qa":       "claude-sonnet-4-6",
}

def create_runner(role: str) -> BaseAgentRunner:
    if AI_BACKEND == "api":
        return APIAgentRunner(model=MODEL_MAP[role])
    return ClaudeCodeAgentRunner()
```

---

## So sánh 2 Modes

| | **Mode B: Claude Code (Default)** | **Mode A: Anthropic API** |
|---|---|---|
| **ENV** | `AI_BACKEND=claude_code` | `AI_BACKEND=api` |
| **Chi phí LLM** | $0 thêm (Pro subscription) | ~$0.18/pipeline run |
| **Cần API credit** | Không | Có |
| **Chạy background 24/7** | Không — cần session mở | Có — fully automated |
| **Trigger từ ngoài** | Không (session-based) | Có — POST /run-pipeline |
| **Phù hợp** | Dev, test, prototype, personal | Production, enterprise, CI/CD |

---

## Ước tính chi phí Mode A

```
1 pipeline run (không caching):
  PM        (Haiku 4.5):  ~2K tokens  → ~$0.001
  Analyser  (Opus 4.7):   ~8K tokens  → ~$0.120
  Engineer  (Sonnet 4.6): ~15K tokens → ~$0.045
  QA        (Sonnet 4.6): ~5K tokens  → ~$0.015
  ─────────────────────────────────────────────
  Tổng:                   ~30K tokens → ~$0.18/run

Với prompt caching (system prompt + spec cached):
  Tiết kiệm ~60-70% phần Analyser → ~$0.09-0.12/run

Ước tính tháng (50 runs): ~$5-9/tháng
```

---

## Lưu ý quan trọng

- Cả 2 modes dùng **cùng Supervisor FSM, cùng ProjectContext, cùng MCP Server**
- Chỉ khác phần LLM backend bên trong mỗi agent
- Strategy: Start với Mode B để develop & validate → switch sang Mode A khi cần production
