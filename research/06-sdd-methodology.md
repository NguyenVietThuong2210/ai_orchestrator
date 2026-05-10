# Research: SDD — Specification-Driven Development

> Ngày research: 2026-05-09

---

## Định nghĩa

**SDD (Specification-Driven Development)** là methodology trong đó **spec (đặc tả) là artifact chính**, code là output được generate từ spec. Spec đóng vai trò là "contract" ràng buộc những gì AI agent được phép generate.

---

## Concept cốt lõi

```
Truyền thống:
  Lập trình viên đọc requirement → viết code trực tiếp

SDD với AI Agents:
  Human viết spec → Analyser agent tinh chỉnh spec
  → [Human Gate: approve spec]
  → Engineer agent generate code từ spec
  → QA agent validate code THEO spec (không phải "cảm tính")
```

**Spec là nguồn sự thật duy nhất** — mọi agent đều reference về spec.

---

## Một spec tốt gồm gì?

| Thành phần | Mô tả |
|---|---|
| **Outcomes** | Thành công trông như thế nào |
| **Scope** | Cái gì trong/ngoài scope |
| **Constraints** | Limitations và requirements |
| **Prior decisions** | Architectural decisions đã được chốt |
| **Task breakdown** | Cách decompose công việc |
| **Verification criteria** | Làm sao biết đã done |

---

## Tại sao SDD quan trọng với AI Orchestrator?

1. **QA có tiêu chí rõ ràng** — Không phụ thuộc vào LLM "đoán" output có đúng không
2. **Parallel agent execution** — Spec cho phép decompose và assign tasks cho nhiều agents song song
3. **Traceability** — Mọi code line đều trace được về spec requirement
4. **Human control** — Human approve spec trước → Human controls gì được build
5. **Reduce hallucination** — Agents bị ràng buộc bởi spec, ít drift hơn

---

## Các tools SDD phổ biến (2025-2026)

| Tool | Stars | Mô tả | Tích hợp |
|---|---|---|---|
| **GitHub Spec Kit** | 93k | CLI + templates + prompts | 30+ AI agents (Cline, Cursor, Copilot...) |
| **Kiro** (AWS) | N/A | AI IDE fork của VS Code | Built-in SDD workflow |
| **cc-sdd** | N/A | Minimal harness cho Claude Code | Claude Code, Cursor, Codex |

### GitHub Spec Kit (được dùng nhiều nhất)
- Python CLI, latest release v0.8.7 (May 7, 2026)
- Cung cấp CLI, templates, prompts
- Tích hợp qua slash commands trong coding assistant
- Support: Cline, Cursor, Copilot, Windsurf, và 25+ agents khác

### Kiro (AWS)
- AI-powered IDE (fork VS Code)
- SDD workflow built-in: Requirements → Design → Tasks → Code generation
- Guided workflow — spec là bước đầu tiên bắt buộc

---

## Áp dụng cho AI Orchestrator

```
Flow với SDD:

User requirement
    ↓
PM Agent → breakdown thành tasks list
    ↓
Analyser Agent → viết Technical Spec (SDD format):
  - API endpoints với input/output schemas
  - Database models
  - Business logic rules
  - Error cases và edge cases
  - Test criteria (pass/fail conditions)
    ↓
[Human Gate] → review và approve spec
    ↓
Engineer Agent → implement code THEO spec (không tự sáng tác)
    ↓
QA Agent → validate code THEO spec
  - Test cases derive từ spec verification criteria
  - Pass: spec được satisfy
  - Fail: liệt kê spec items chưa được satisfy
```

---

## Nguồn
- [Martin Fowler: Understanding SDD — Kiro, spec-kit, and Tessl](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
- [SDD — AI First Coding Practice (Medium)](https://medium.com/ai-pace/specification-driven-development-sdd-ai-first-coding-practice-e8f4cc3c2fc4)
- [Spec-Driven Development: From Code to Contract (ArXiv)](https://arxiv.org/html/2602.00180v1)
- [GitHub Spec Kit](https://github.com/github/spec-kit)
