---
name: present
description: Convert a markdown file into a beautiful, self-contained Vietnamese HTML presentation in SOLUTION.html style. Use for customer-facing demos, architecture overviews, process/workflow documentation.
argument-hint: <path-to-markdown-file>
user-invocable: true
disable-model-invocation: false
---

# Skill: /present

Convert any `.md` file into a beautiful Vietnamese HTML presentation.
Style reference: `SOLUTION.html` in the project root (dark theme, card layout, pipeline diagrams, stat tiles).

## When to use

- `/present SOLUTION.md` — generate customer presentation of the architecture
- `/present docs/api.md` — generate HTML API reference
- `/present specs/spec.md` — generate visual spec for review
- `/present README.md` — generate project overview for stakeholders

## Workflow (9 steps)

### Step 1 — Read input
Read the full content of the `.md` file passed as the argument.
If no argument is given, ask the user: "Which markdown file should I convert?"

### Step 2 — Analyze structure
Identify:
- H1 headings → hero sections
- H2 headings → main card sections
- H3 headings → sub-cards or bullet lists
- Tables → data grids
- Code blocks → code showcase panels
- Mermaid diagrams → convert to styled ASCII pipeline nodes if renderable, otherwise styled code panel
- Bullet lists → feature card grids or bullet list cards
- Bold terms → highlight badges

### Step 3 — Classify content type
Determine the dominant content type to choose layout hints:
- `process_flow` — lots of steps, arrows, pipeline nodes
- `architecture` — layers (Client / API / Engine / Storage)
- `feature_spec` — requirements, acceptance criteria, DoD
- `api_reference` — endpoints, request/response tables
- `business` — goals, KPIs, stakeholders, timelines
- `general` — default card layout

### Step 4 — Map sections to components
For each H2 section, choose the best HTML component:

| Content pattern | Component |
|---|---|
| H2 + table with ≥3 columns | Data grid card |
| H2 + bullet list | Feature cards grid (3 cols) |
| H2 + code block | Code showcase panel |
| H2 + "Changelog" or "Lịch sử" | Timeline card |
| H2 + numbered steps | Ordered step list |
| H2 + H3 children | Nested section with sub-cards |
| H2 + metrics/numbers | Stat tiles row |
| H1 | Hero section (full-width banner) |

### Step 5 — Generate HTML
Produce a **single, fully self-contained HTML file** using the CSS template below.
Rules:
- All CSS must be in a `<style>` block in `<head>` — no external CDN links
- All content is in the `<body>` — no JS frameworks, no React
- Use semantic HTML: `<section>`, `<article>`, `<header>`, `<footer>`
- Every card must have a non-empty content area

### Step 6 — Inject Vietnamese context
- Translate section titles: "Overview" → "Tổng Quan", "Architecture" → "Kiến Trúc", "Endpoints" → "API Endpoints", "Features" → "Tính Năng", "Requirements" → "Yêu Cầu", "Deployment" → "Triển Khai"
- For technical concepts (LangGraph, SSE, TypedDict, asyncpg), add a small italic tooltip: `<em class="tooltip">Giải thích: ...</em>`
- Keep code blocks and technical identifiers in English
- Numbers and data stay as-is

### Step 7 — Write output file
Determine output path:
- If input is `foo/bar.md`, write `foo/bar-presentation.html`
- If a `presentations/` directory exists in the project root, write there instead: `presentations/bar.html`

Use the Write tool to create the file.

### Step 8 — Quality check
Before writing, verify:
- [ ] At least one `<section>` with real content
- [ ] No unclosed `<div>` tags (count opens vs closes)
- [ ] Hero section has the document H1 title
- [ ] CSS `<style>` block is present
- [ ] `<meta charset="UTF-8">` is present
- [ ] File size is reasonable (> 3KB)

### Step 9 — Report
Tell the user:
```
✅ Presentation created: <output-path>
   Sections: <N>   Components used: <list>
   To open: start <output-path>   (Windows)  |  open <output-path>  (Mac)
```

---

## HTML Template & CSS

Use this as your base. Replace `{{TITLE}}`, `{{DATE}}`, and section content.

```html
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}}</title>
<style>
  :root {
    --primary: #6366f1;
    --primary-dark: #4f46e5;
    --accent: #06b6d4;
    --green: #10b981;
    --yellow: #f59e0b;
    --red: #ef4444;
    --purple: #8b5cf6;
    --teal: #14b8a6;
    --bg: #0f0f1a;
    --bg2: #1a1a2e;
    --bg3: #16213e;
    --card: #1e1e35;
    --border: #2d2d50;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --text-dim: #64748b;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg); color: var(--text);
    line-height: 1.6; min-height: 100vh;
  }
  /* Navigation */
  nav {
    position: sticky; top: 0; z-index: 100;
    background: rgba(15,15,26,0.95); backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
    padding: 0.75rem 2rem; display: flex; align-items: center; gap: 2rem;
  }
  nav .brand { font-weight: 700; font-size: 1rem; color: var(--primary); }
  nav .nav-links { display: flex; gap: 1.5rem; list-style: none; }
  nav .nav-links a { color: var(--text-muted); text-decoration: none; font-size: 0.85rem; transition: color 0.2s; }
  nav .nav-links a:hover { color: var(--text); }
  /* Hero */
  .hero {
    background: linear-gradient(135deg, var(--bg2) 0%, var(--bg3) 50%, rgba(99,102,241,0.1) 100%);
    padding: 5rem 2rem 4rem; text-align: center; border-bottom: 1px solid var(--border);
    position: relative; overflow: hidden;
  }
  .hero::before {
    content: ''; position: absolute; inset: 0;
    background: radial-gradient(circle at 30% 50%, rgba(99,102,241,0.08) 0%, transparent 60%),
                radial-gradient(circle at 70% 50%, rgba(6,182,212,0.06) 0%, transparent 60%);
  }
  .hero-label {
    display: inline-block; background: rgba(99,102,241,0.15);
    color: var(--primary); padding: 0.3rem 0.8rem; border-radius: 99px;
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase;
    margin-bottom: 1rem; border: 1px solid rgba(99,102,241,0.3);
  }
  .hero h1 {
    font-size: clamp(2rem, 5vw, 3.5rem); font-weight: 800; line-height: 1.2;
    background: linear-gradient(135deg, var(--text) 0%, var(--primary) 50%, var(--accent) 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    margin-bottom: 1rem;
  }
  .hero-sub {
    font-size: 1.1rem; color: var(--text-muted); max-width: 600px; margin: 0 auto 2rem;
  }
  /* Container */
  .container { max-width: 1100px; margin: 0 auto; padding: 0 2rem; }
  /* Section */
  section { padding: 4rem 0; border-bottom: 1px solid var(--border); }
  section:last-of-type { border-bottom: none; }
  .section-label {
    display: inline-block; background: rgba(99,102,241,0.12);
    color: var(--primary); padding: 0.25rem 0.7rem; border-radius: 99px;
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
    margin-bottom: 0.75rem;
  }
  .section-title {
    font-size: 1.8rem; font-weight: 700; color: var(--text); margin-bottom: 0.5rem;
  }
  .section-sub { color: var(--text-muted); font-size: 0.95rem; max-width: 600px; margin-bottom: 2.5rem; }
  /* Cards */
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 1.5rem; transition: border-color 0.2s;
  }
  .card:hover { border-color: rgba(99,102,241,0.4); }
  .cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; }
  .cards-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
  .card-icon { font-size: 1.5rem; margin-bottom: 0.75rem; }
  .card-title { font-size: 0.95rem; font-weight: 700; color: var(--text); margin-bottom: 0.4rem; }
  .card-body { font-size: 0.85rem; color: var(--text-muted); line-height: 1.6; }
  /* Stat tiles */
  .stat-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1.5rem 0; }
  .stat-tile {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 1.25rem; text-align: center;
  }
  .stat-num { font-size: 2rem; font-weight: 800; color: var(--primary); }
  .stat-label { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem; }
  /* Data table */
  .data-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  .data-table th {
    background: rgba(99,102,241,0.1); color: var(--primary);
    padding: 0.6rem 1rem; text-align: left; font-weight: 600; border-bottom: 1px solid var(--border);
  }
  .data-table td { padding: 0.6rem 1rem; border-bottom: 1px solid var(--border); color: var(--text-muted); }
  .data-table tr:last-child td { border-bottom: none; }
  .data-table tr:nth-child(even) td { background: rgba(255,255,255,0.02); }
  .data-table tr:hover td { background: rgba(99,102,241,0.05); }
  /* Code */
  .code-block {
    background: #0d1117; border: 1px solid var(--border); border-radius: 10px;
    padding: 1.25rem; font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 0.8rem; color: #c9d1d9; overflow-x: auto; line-height: 1.7;
  }
  .code-block .kw { color: #ff7b72; }
  .code-block .str { color: #a5d6ff; }
  .code-block .cmt { color: #8b949e; font-style: italic; }
  /* Timeline */
  .timeline { display: flex; flex-direction: column; gap: 1rem; }
  .timeline-item {
    border-left: 3px solid var(--primary); padding-left: 1rem; padding-bottom: 0.5rem;
  }
  .timeline-item .tl-date { font-size: 0.75rem; color: var(--primary); font-weight: 700; margin-bottom: 0.25rem; }
  .timeline-item .tl-title { font-weight: 600; color: var(--text); margin-bottom: 0.25rem; }
  .timeline-item .tl-body { font-size: 0.85rem; color: var(--text-muted); }
  /* Highlight box */
  .highlight-box {
    background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(6,182,212,0.05));
    border: 1px solid rgba(99,102,241,0.25); border-radius: 12px;
    padding: 1.5rem; margin: 1.5rem 0;
  }
  .highlight-box h3 { color: var(--primary); margin-bottom: 0.5rem; }
  /* Tooltip */
  .tooltip { color: var(--text-dim); font-size: 0.8rem; margin-left: 0.25rem; }
  /* Badge */
  .badge {
    display: inline-block; padding: 0.15rem 0.5rem; border-radius: 99px;
    font-size: 0.7rem; font-weight: 600; margin-left: 0.25rem;
  }
  .badge-green  { background: rgba(16,185,129,0.15); color: var(--green); }
  .badge-yellow { background: rgba(245,158,11,0.15); color: var(--yellow); }
  .badge-red    { background: rgba(239,68,68,0.15);  color: var(--red); }
  .badge-blue   { background: rgba(99,102,241,0.15); color: var(--primary); }
  /* Pipeline nodes */
  .pipeline-row { display: flex; align-items: center; flex-wrap: wrap; gap: 0; justify-content: center; padding: 0.5rem 0; }
  .pipe-node { display: flex; flex-direction: column; align-items: center; }
  .pipe-icon {
    width: 52px; height: 52px; border-radius: 12px; display: flex; align-items: center;
    justify-content: center; font-size: 1.3rem; border: 2px solid;
  }
  .pipe-label { font-size: 0.65rem; font-weight: 700; text-align: center; color: var(--text-muted); max-width: 64px; line-height: 1.3; margin-top: 0.25rem; }
  .pipe-arrow {
    width: 24px; height: 2px; background: linear-gradient(90deg, var(--border), var(--primary));
    position: relative; flex-shrink: 0; align-self: center; margin-bottom: 1.4rem;
  }
  .pipe-arrow::after {
    content: ''; position: absolute; right: -4px; top: -4px;
    border: 5px solid transparent; border-left-color: var(--primary);
  }
  /* Footer */
  footer {
    background: var(--bg2); border-top: 1px solid var(--border);
    padding: 2rem; text-align: center; color: var(--text-dim); font-size: 0.85rem;
  }
  footer strong { color: var(--text-muted); }
  /* Responsive */
  @media (max-width: 640px) {
    .cards-3 { grid-template-columns: 1fr; }
    .hero h1 { font-size: 1.8rem; }
    nav .nav-links { display: none; }
  }
</style>
</head>
<body>

<nav>
  <span class="brand">🤖 {{TITLE}}</span>
  <ul class="nav-links">
    <!-- Add <li><a href="#section-id">Tên Mục</a></li> for each H2 section -->
  </ul>
</nav>

<!-- HERO: maps from H1 -->
<div class="hero">
  <div class="container" style="position:relative; z-index:1;">
    <div class="hero-label">Tài liệu trình bày</div>
    <h1>{{TITLE}}</h1>
    <p class="hero-sub">{{SUBTITLE_FROM_FIRST_PARAGRAPH}}</p>
  </div>
</div>

<!-- Each H2 becomes a <section> -->
<section id="section-1">
  <div class="container">
    <div class="section-label">Mục 1</div>
    <h2 class="section-title">{{H2_TITLE}}</h2>
    <p class="section-sub">{{H2_INTRO}}</p>

    <!-- Feature cards grid (from bullet list) -->
    <div class="cards-3">
      <div class="card">
        <div class="card-icon">🎯</div>
        <div class="card-title">{{FEATURE_NAME}}</div>
        <div class="card-body">{{FEATURE_DESC}}</div>
      </div>
    </div>

    <!-- Data table (from markdown table) -->
    <table class="data-table">
      <thead><tr><th>Cột 1</th><th>Cột 2</th><th>Cột 3</th></tr></thead>
      <tbody>
        <tr><td>Dữ liệu</td><td>Dữ liệu</td><td>Dữ liệu</td></tr>
      </tbody>
    </table>

    <!-- Code block (from fenced code) -->
    <div class="code-block">{{CODE_CONTENT}}</div>

    <!-- Stat tiles (from metrics/numbers) -->
    <div class="stat-tiles">
      <div class="stat-tile">
        <div class="stat-num">42</div>
        <div class="stat-label">Chỉ số</div>
      </div>
    </div>

    <!-- Timeline (from changelog) -->
    <div class="timeline">
      <div class="timeline-item">
        <div class="tl-date">v1.0 — 2026-01-01</div>
        <div class="tl-title">Tiêu đề thay đổi</div>
        <div class="tl-body">Mô tả thay đổi.</div>
      </div>
    </div>

    <!-- Highlight box (for important callouts) -->
    <div class="highlight-box">
      <h3>💡 Điểm quan trọng</h3>
      <p style="color: var(--text-muted);">{{IMPORTANT_NOTE}}</p>
    </div>
  </div>
</section>

<footer>
  <p>🤖 <strong>{{TITLE}}</strong></p>
  <p style="margin-top: 0.5rem; color: var(--text-dim);">
    Được tạo bởi AI Orchestrator · {{DATE}}
  </p>
</footer>

</body>
</html>
```

## Vietnamese Translation Cheat Sheet

| English | Tiếng Việt |
|---|---|
| Overview | Tổng Quan |
| Architecture | Kiến Trúc Hệ Thống |
| Features | Tính Năng |
| Requirements | Yêu Cầu |
| API Endpoints | Điểm Cuối API |
| Database | Cơ Sở Dữ Liệu |
| Authentication | Xác Thực |
| Deployment | Triển Khai |
| Security | Bảo Mật |
| Performance | Hiệu Suất |
| Configuration | Cấu Hình |
| Installation | Cài Đặt |
| Getting Started | Bắt Đầu |
| Changelog | Lịch Sử Phiên Bản |
| Known Issues | Vấn Đề Đã Biết |
| Contributing | Đóng Góp |
| License | Giấy Phép |
| Contact | Liên Hệ |
| Pipeline | Quy Trình |
| Workflow | Luồng Công Việc |
| Agent | Tác Nhân AI |
| Checkpoint | Điểm Lưu Trữ |
| Routing | Định Tuyến |
| Intent | Mục Đích |

## Technical Tooltip Phrases

Add these inline after technical terms:
- LangGraph → `<em class="tooltip">— thư viện điều phối AI với checkpoint tự động</em>`
- AsyncPostgresSaver → `<em class="tooltip">— lưu trạng thái vào PostgreSQL sau mỗi bước</em>`
- SSE → `<em class="tooltip">— Server-Sent Events: stream sự kiện thời gian thực</em>`
- TypedDict → `<em class="tooltip">— kiểu dữ liệu Python có kiểm tra tại compile time</em>`
- FastAPI → `<em class="tooltip">— web framework Python hiệu năng cao</em>`

## Node Color Classes (for pipeline diagrams)

```css
.node-pm      { background: rgba(139,92,246,0.2);  border-color: rgba(139,92,246,0.5); }
.node-analyse { background: rgba(6,182,212,0.2);   border-color: rgba(6,182,212,0.5);  }
.node-gate    { background: rgba(245,158,11,0.2);  border-color: rgba(245,158,11,0.5); }
.node-eng     { background: rgba(249,115,22,0.2);  border-color: rgba(249,115,22,0.5); }
.node-review  { background: rgba(234,179,8,0.2);   border-color: rgba(234,179,8,0.5);  }
.node-sec     { background: rgba(239,68,68,0.2);   border-color: rgba(239,68,68,0.5);  }
.node-qa      { background: rgba(16,185,129,0.2);  border-color: rgba(16,185,129,0.5); }
.node-deploy  { background: rgba(20,184,166,0.2);  border-color: rgba(20,184,166,0.5); }
.node-retro   { background: rgba(99,102,241,0.2);  border-color: rgba(99,102,241,0.5); }
.node-done    { background: rgba(16,185,129,0.3);  border-color: rgba(16,185,129,0.8); }
```
