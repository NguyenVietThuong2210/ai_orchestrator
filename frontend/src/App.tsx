import { useState, useEffect, useCallback } from "react";
import { usePipeline } from "./hooks/usePipeline";
import { AgentTimeline } from "./components/AgentTimeline";
import { SpecReview } from "./components/SpecReview";
import { ArtifactList } from "./components/ArtifactList";
import { TestReport } from "./components/TestReport";
import { PipelineForm } from "./components/PipelineForm";
import { ProjectsBrowser } from "./components/ProjectsBrowser";
import { api } from "./api/client";
import type {
  PipelineStatus, Task, CodeReviewReport, SecurityReport,
  DeployReport, Retrospective, SpecAnalysisReport, UserMessage,
} from "./types";

// ── Step definitions ──────────────────────────────────────────────────────────

const STEPS = [
  { key: "pm",            label: "PM",        icon: "📋", color: "violet" },
  { key: "clarify",       label: "Clarify",   icon: "❓", color: "yellow" },
  { key: "analyser",      label: "Analyse",   icon: "🔍", color: "cyan"   },
  { key: "spec_analyze",  label: "Spec QA",   icon: "📐", color: "cyan"   },
  { key: "task_decomp",   label: "Tasks",     icon: "🗂",  color: "cyan"   },
  { key: "gate",          label: "Review",    icon: "👤", color: "amber"  },
  { key: "engineer",      label: "Engineer",  icon: "⚙️", color: "orange" },
  { key: "reviewer",      label: "Code Rev",  icon: "🔎", color: "yellow" },
  { key: "security",      label: "Security",  icon: "🛡",  color: "red"    },
  { key: "qa",            label: "QA",        icon: "✅", color: "green"  },
  { key: "deploy",        label: "Deploy",    icon: "🚀", color: "teal"   },
  { key: "retrospective", label: "Retro",     icon: "📊", color: "indigo" },
] as const;

const NODE_TO_STEP: Record<string, string> = {
  pm: "pm", clarification_gate: "clarify", analyser: "analyser",
  spec_analyze: "spec_analyze", task_decompose: "task_decomp",
  human_gate: "gate", engineer: "engineer", reviewer: "reviewer",
  security: "security", qa: "qa", deploy: "deploy", retrospective: "retrospective",
};

const STEP_ORDER: string[] = STEPS.map((s) => s.key);
type StepState = "done" | "active" | "pending" | "error";

function getStepState(key: string, status: PipelineStatus, currentNode: string | null): StepState {
  const idx = STEP_ORDER.indexOf(key);
  if (status === "done") return "done";
  if (status === "failed") {
    const active = currentNode ? NODE_TO_STEP[currentNode] : null;
    const aIdx = active ? STEP_ORDER.indexOf(active) : -1;
    if (idx < aIdx) return "done";
    if (idx === aIdx) return "error";
    return "pending";
  }
  const active =
    status === "starting"               ? "pm"
    : status === "waiting_clarification"? "clarify"
    : status === "waiting_approval"     ? "gate"
    : currentNode                       ? NODE_TO_STEP[currentNode] ?? null
    : null;
  const aIdx = active ? STEP_ORDER.indexOf(active) : -1;
  if (aIdx > idx) return "done";
  if (aIdx === idx) return "active";
  return "pending";
}

// ── Pipeline progress bar ─────────────────────────────────────────────────────

function PipelineBar({ status, currentNode }: { status: PipelineStatus; currentNode: string | null }) {
  return (
    <div className="flex items-center gap-0 overflow-x-auto py-1 px-2">
      {STEPS.map(({ key, label, icon }, i) => {
        const s = getStepState(key, status, currentNode);
        const isLast = i === STEPS.length - 1;
        return (
          <div key={key} className="flex items-center shrink-0">
            <div className="flex flex-col items-center gap-0.5">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold border-2 transition-all duration-300
                ${s === "done"   ? "bg-emerald-500 border-emerald-400 text-white shadow-emerald-500/30 shadow-md"
                : s === "active" ? "bg-indigo-500 border-indigo-300 text-white ring-2 ring-indigo-300/50 animate-pulse shadow-indigo-500/40 shadow-lg"
                : s === "error"  ? "bg-red-500 border-red-400 text-white shadow-red-500/30 shadow-md"
                :                  "bg-slate-700 border-slate-600 text-slate-500"}`}>
                {s === "done" ? "✓" : s === "error" ? "✗" : icon}
              </div>
              <span className={`text-[9px] font-semibold whitespace-nowrap
                ${s === "done"   ? "text-emerald-400"
                : s === "active" ? "text-indigo-300"
                : s === "error"  ? "text-red-400"
                :                  "text-slate-600"}`}>
                {label}
              </span>
            </div>
            {!isLast && (
              <div className={`h-px w-3 mx-0.5 shrink-0 transition-colors duration-300
                ${s === "done" ? "bg-emerald-500" : "bg-slate-700"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Status badge ──────────────────────────────────────────────────────────────

const STATUS_CFG: Record<PipelineStatus, { label: string; dot: string; cls: string }> = {
  idle:                  { label: "Idle",          dot: "bg-slate-500",   cls: "text-slate-400 border-slate-700"    },
  starting:              { label: "Starting…",     dot: "bg-blue-400 animate-pulse",    cls: "text-blue-300 border-blue-700"    },
  running:               { label: "Running",       dot: "bg-blue-400 animate-pulse",    cls: "text-blue-300 border-blue-700"    },
  waiting_clarification: { label: "Needs Info",    dot: "bg-violet-400 animate-pulse",  cls: "text-violet-300 border-violet-700"},
  waiting_approval:      { label: "Needs Review",  dot: "bg-amber-400 animate-pulse",   cls: "text-amber-300 border-amber-700"  },
  done:                  { label: "Done",          dot: "bg-emerald-400", cls: "text-emerald-300 border-emerald-700" },
  failed:                { label: "Failed",        dot: "bg-red-400",     cls: "text-red-300 border-red-700"         },
};

function StatusBadge({ status }: { status: PipelineStatus }) {
  const { label, dot, cls } = STATUS_CFG[status];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${cls} bg-slate-900/60`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  );
}

// ── Intent badge ──────────────────────────────────────────────────────────────

const INTENT_CFG: Record<string, { label: string; icon: string; cls: string }> = {
  feature: { label: "Feature",  icon: "✨", cls: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"  },
  query:   { label: "Query",    icon: "🔍", cls: "bg-slate-500/20 text-slate-300 border-slate-500/30"    },
  test:    { label: "Test",     icon: "🧪", cls: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"},
  bug_fix: { label: "Bug Fix",  icon: "🐛", cls: "bg-red-500/20 text-red-300 border-red-500/30"          },
  review:  { label: "Review",   icon: "🔎", cls: "bg-violet-500/20 text-violet-300 border-violet-500/30"  },
};

function IntentBadge({ intent }: { intent: string }) {
  const cfg = INTENT_CFG[intent] ?? INTENT_CFG.feature;
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-semibold border ${cfg.cls}`}>
      {cfg.icon} {cfg.label}
    </span>
  );
}

// ── Copy button ───────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }, [text]);
  return (
    <button onClick={copy} title="Copy job ID"
      className="font-mono text-xs text-slate-500 hover:text-slate-200 px-2 py-1 rounded hover:bg-slate-700 transition-colors">
      {copied ? "✓ copied" : text.slice(0, 10) + "…"}
    </button>
  );
}

// ── Sprint board ──────────────────────────────────────────────────────────────

const PRIORITY_CFG = {
  1: { label: "P1", cls: "bg-red-500/20 text-red-300 border-red-500/30",    dot: "bg-red-400"    },
  2: { label: "P2", cls: "bg-amber-500/20 text-amber-300 border-amber-500/30", dot: "bg-amber-400" },
  3: { label: "P3", cls: "bg-blue-500/20 text-blue-300 border-blue-500/30",  dot: "bg-blue-400"   },
} as Record<number, { label: string; cls: string; dot: string }>;

function SprintBoard({ tasks, dod }: { tasks: Task[]; dod: string[] }) {
  if (!tasks.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-500">
        <div className="w-16 h-16 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-3xl">📋</div>
        <div className="text-center">
          <p className="text-sm font-semibold text-slate-400">Chưa có task nào</p>
          <p className="text-xs mt-1">PM đang phân tích yêu cầu…</p>
        </div>
      </div>
    );
  }

  const byPhase = tasks.reduce<Record<string, Task[]>>((acc, t) => {
    const ph = (t as Task & { phase?: string }).phase ?? "General";
    (acc[ph] ??= []).push(t);
    return acc;
  }, {});

  return (
    <div className="space-y-5">
      {dod.length > 0 && (
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-emerald-400 mb-2">Definition of Done</p>
          <ul className="space-y-1.5">
            {dod.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                <span className="text-emerald-500 mt-0.5 shrink-0">□</span>{c}
              </li>
            ))}
          </ul>
        </div>
      )}
      {Object.entries(byPhase).map(([phase, pTasks]) => (
        <div key={phase}>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">{phase}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-700 text-slate-400">{pTasks.length}</span>
          </div>
          <div className="space-y-2">
            {pTasks.map((t) => {
              const pCfg = PRIORITY_CFG[t.priority] ?? PRIORITY_CFG[3];
              const tExt = t as Task & { phase?: string; parallel?: boolean };
              return (
                <div key={t.id} className="group rounded-xl border border-slate-700 bg-slate-800/60 p-3 hover:border-slate-600 hover:bg-slate-800 transition-all">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border font-bold ${pCfg.cls}`}>{pCfg.label}</span>
                    <span className="text-[10px] font-mono text-slate-600">{t.id}</span>
                    {tExt.parallel && (
                      <span className="text-[10px] px-1 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">‖ parallel</span>
                    )}
                    <span className={`ml-auto w-2 h-2 rounded-full ${t.status === "done" ? "bg-emerald-400" : "bg-slate-600"}`} />
                  </div>
                  <p className="text-sm font-semibold text-slate-200 mb-1">{t.title}</p>
                  {t.description && <p className="text-xs text-slate-500 leading-relaxed">{t.description}</p>}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── SDD panel ─────────────────────────────────────────────────────────────────

function SddPanel({ specMd, planMd, tasksMd, constitution }: {
  specMd: string; planMd: string; tasksMd: string; constitution: string;
}) {
  const [tab, setTab] = useState<"spec" | "plan" | "tasks" | "constitution">("spec");
  const tabs = [
    { key: "spec" as const,         label: "spec.md",          has: !!specMd       },
    { key: "plan" as const,         label: "plan.md",          has: !!planMd       },
    { key: "tasks" as const,        label: "tasks.md",         has: !!tasksMd      },
    { key: "constitution" as const, label: "constitution.md",  has: !!constitution },
  ];
  const content = tab === "spec" ? specMd : tab === "plan" ? planMd : tab === "tasks" ? tasksMd : constitution;

  return (
    <div className="flex flex-col h-full gap-3">
      <div className="flex gap-1">
        {tabs.map(({ key, label, has }) => (
          <button key={key} onClick={() => has && setTab(key)} disabled={!has}
            className={`text-xs px-3 py-1.5 rounded-lg font-mono font-semibold transition-all
              ${tab === key    ? "bg-indigo-600 text-white shadow"
              : has            ? "bg-slate-700 text-slate-300 hover:bg-slate-600"
              :                  "bg-slate-800 text-slate-600 cursor-not-allowed opacity-50"}`}>
            {label}
          </button>
        ))}
      </div>
      {content
        ? <pre className="flex-1 overflow-auto text-xs font-mono bg-slate-900 border border-slate-700 rounded-xl p-4 whitespace-pre-wrap leading-relaxed text-slate-300">
            {content}
          </pre>
        : <EmptyCard icon="📄" title="Chưa được tạo" sub="Artifact sẽ xuất hiện sau khi agent hoàn thành" />
      }
    </div>
  );
}

// ── Spec analysis panel ───────────────────────────────────────────────────────

function SpecAnalysisPanel({ report }: { report: SpecAnalysisReport }) {
  const SEV_CFG: Record<string, string> = {
    CRITICAL: "bg-red-500/20 text-red-300 border-red-500/30",
    HIGH:     "bg-orange-500/20 text-orange-300 border-orange-500/30",
    MEDIUM:   "bg-amber-500/20 text-amber-300 border-amber-500/30",
    LOW:      "bg-slate-700 text-slate-400 border-slate-600",
  };
  return (
    <div className="space-y-4">
      <div className={`rounded-xl border p-4 flex items-center gap-3 ${report.approved ? "bg-emerald-500/10 border-emerald-500/30" : "bg-amber-500/10 border-amber-500/30"}`}>
        <span className="text-2xl">{report.approved ? "✅" : "🔄"}</span>
        <div>
          <p className={`font-semibold text-sm ${report.approved ? "text-emerald-300" : "text-amber-300"}`}>
            {report.approved ? "Spec đạt yêu cầu" : "Spec cần chỉnh sửa"}
          </p>
          {report.summary && <p className="text-xs mt-0.5 text-slate-400">{report.summary}</p>}
        </div>
      </div>
      {report.findings.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Findings ({report.findings.length})</p>
          {report.findings.map((f, i) => (
            <div key={i} className={`rounded-xl border p-3 ${SEV_CFG[f.severity] ?? SEV_CFG.LOW}`}>
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-black/20">{f.severity}</span>
                <span className="text-[10px] font-mono opacity-70">{f.pass_name}</span>
                <span className="text-[10px] ml-auto opacity-60">{f.location}</span>
              </div>
              <p className="text-xs font-medium mb-1">{f.description}</p>
              {f.suggestion && <p className="text-[11px] italic opacity-70">→ {f.suggestion}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Code review panel ─────────────────────────────────────────────────────────

function CodeReviewPanel({ report }: { report: CodeReviewReport }) {
  const pass = report.status === "pass";
  return (
    <div className="space-y-4">
      <div className={`rounded-xl border p-4 flex items-center gap-3 ${pass ? "bg-emerald-500/10 border-emerald-500/30" : "bg-red-500/10 border-red-500/30"}`}>
        <span className="text-2xl">{pass ? "✅" : "🔄"}</span>
        <div>
          <p className={`font-semibold text-sm ${pass ? "text-emerald-300" : "text-red-300"}`}>
            {pass ? "Code Review: Passed" : "Code Review: Failed — gửi lại Engineer"}
          </p>
          {report.summary && <p className="text-xs mt-0.5 text-slate-400">{report.summary}</p>}
        </div>
      </div>
      {(report.issues ?? []).length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Issues ({report.issues.length})</p>
          {report.issues.map((issue, i) => (
            <div key={i} className="rounded-xl border border-slate-700 bg-slate-800/60 p-3">
              <div className="flex items-center gap-2 mb-1.5">
                <span className={`text-[10px] px-1.5 py-0.5 rounded border font-bold
                  ${issue.severity === "major" ? "bg-red-500/20 text-red-300 border-red-500/30" : "bg-amber-500/20 text-amber-300 border-amber-500/30"}`}>
                  {issue.severity}
                </span>
                <span className="font-mono text-xs text-slate-500">{issue.file}:{issue.line}</span>
              </div>
              <p className="text-xs text-slate-300">{issue.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Security panel ────────────────────────────────────────────────────────────

function SecurityPanel({ report }: { report: SecurityReport }) {
  const CFG = {
    pass: { cls: "bg-emerald-500/10 border-emerald-500/30", icon: "🛡", label: "Clean — không có lỗ hổng", text: "text-emerald-300" },
    warn: { cls: "bg-amber-500/10 border-amber-500/30",     icon: "⚠️", label: "Cảnh báo — chỉ có low severity", text: "text-amber-300" },
    fail: { cls: "bg-red-500/10 border-red-500/30",         icon: "🚨", label: "Thất bại — lỗ hổng nghiêm trọng", text: "text-red-300"  },
  };
  const cfg = CFG[report.status] ?? CFG.fail;
  return (
    <div className="space-y-4">
      <div className={`rounded-xl border p-4 flex items-center gap-3 ${cfg.cls}`}>
        <span className="text-2xl">{cfg.icon}</span>
        <div>
          <p className={`font-semibold text-sm ${cfg.text}`}>{cfg.label}</p>
          {report.summary && <p className="text-xs mt-0.5 text-slate-400">{report.summary}</p>}
        </div>
      </div>
      {(report.vulnerabilities ?? []).length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Vulnerabilities ({report.vulnerabilities.length})</p>
          {report.vulnerabilities.map((v, i) => (
            <div key={i} className="rounded-xl border border-slate-700 bg-slate-800/60 p-3">
              <div className="flex items-center gap-2 mb-1.5">
                <span className={`text-[10px] px-1.5 py-0.5 rounded border font-bold
                  ${(v.severity === "HIGH" || v.severity === "CRITICAL") ? "bg-red-500/20 text-red-300 border-red-500/30"
                  : v.severity === "MEDIUM" ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
                  : "bg-slate-700 text-slate-400 border-slate-600"}`}>
                  {v.severity}
                </span>
                <span className="font-mono text-xs text-indigo-400">{v.tool} {v.id}</span>
                {v.file && <span className="text-xs text-slate-500 ml-auto">{v.file}</span>}
              </div>
              <p className="text-xs text-slate-300">{v.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Deploy panel ──────────────────────────────────────────────────────────────

function DeployPanel({ report }: { report: DeployReport }) {
  const pass = report.status === "pass";
  return (
    <div className="space-y-4">
      <div className={`rounded-xl border p-4 flex items-center gap-3 ${pass ? "bg-emerald-500/10 border-emerald-500/30" : "bg-red-500/10 border-red-500/30"}`}>
        <span className="text-2xl">{pass ? "🚀" : "💥"}</span>
        <p className={`font-semibold text-sm ${pass ? "text-emerald-300" : "text-red-300"}`}>
          {pass ? "Deploy thành công & Smoke Test pass" : "Deploy hoặc Smoke Test thất bại"}
        </p>
      </div>
      <div className="rounded-xl border border-slate-700 bg-slate-800/60 p-4 space-y-3">
        {[
          { label: "Endpoint", value: report.endpoint || "—", mono: true },
          { label: "Response", value: report.response || "—", mono: true },
          { label: "Command",  value: report.command_used || "—", mono: true },
        ].map(({ label, value, mono }) => (
          <div key={label} className="flex gap-3 text-sm">
            <span className="text-slate-500 w-20 shrink-0">{label}</span>
            <span className={`text-slate-300 ${mono ? "font-mono text-xs" : ""}`}>{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Retrospective panel ───────────────────────────────────────────────────────

function RetroPanel({ retro }: { retro: Retrospective }) {
  const metrics = retro.metrics ?? {};
  return (
    <div className="space-y-6">
      {Object.keys(metrics).length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(metrics).map(([k, v]) => (
            <div key={k} className="rounded-xl border border-slate-700 bg-slate-800/60 px-3 py-3 text-center">
              <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-1">{k.replace(/_/g, " ")}</p>
              <p className="text-xl font-bold text-slate-200">{String(v)}</p>
            </div>
          ))}
        </div>
      )}
      {retro.what_worked?.length > 0 && (
        <Section title="✅ Hoạt động tốt" color="text-emerald-400">
          {retro.what_worked.map((x, i) => <Item key={i} icon="✓" cls="text-emerald-500" text={x} />)}
        </Section>
      )}
      {retro.what_failed?.length > 0 && (
        <Section title="❌ Cần cải thiện" color="text-red-400">
          {retro.what_failed.map((x, i) => <Item key={i} icon="✗" cls="text-red-500" text={x} />)}
        </Section>
      )}
      {retro.lessons?.length > 0 && (
        <Section title="💡 Bài học kinh nghiệm" color="text-indigo-400">
          {retro.lessons.map((x, i) => <Item key={i} icon="→" cls="text-indigo-400" text={x} />)}
        </Section>
      )}
    </div>
  );
}

function Section({ title, color, children }: { title: string; color: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className={`text-xs font-bold uppercase tracking-wider mb-3 ${color}`}>{title}</h3>
      <ul className="space-y-2">{children}</ul>
    </div>
  );
}

function Item({ icon, cls, text }: { icon: string; cls: string; text: string }) {
  return (
    <li className="flex items-start gap-2 text-sm text-slate-300">
      <span className={`shrink-0 font-bold mt-0.5 ${cls}`}>{icon}</span>{text}
    </li>
  );
}

// ── Inject panel ──────────────────────────────────────────────────────────────

function InjectPanel({ jobId, queue }: { jobId: string; queue: UserMessage[] }) {
  const [msg, setMsg] = useState("");
  const [target, setTarget] = useState("any");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const send = useCallback(async () => {
    if (!msg.trim() || !jobId) return;
    setSending(true);
    try {
      await api.injectMessage(jobId, msg.trim(), target);
      setSent(true);
      setMsg("");
      setTimeout(() => setSent(false), 2000);
    } catch { }
    finally { setSending(false); }
  }, [jobId, msg, target]);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-4">
        <p className="text-sm font-semibold text-indigo-300 mb-1">💬 Inject Message vào Pipeline</p>
        <p className="text-xs text-slate-400">Gửi context hoặc hướng dẫn đến agent tiếp theo đang chạy. Message được queue và drain tại node kế tiếp.</p>
      </div>
      <div className="space-y-3">
        <div>
          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide block mb-1.5">Target Agent</label>
          <select value={target} onChange={(e) => setTarget(e.target.value)}
            className="w-full text-sm px-3 py-2 rounded-xl border border-slate-700 bg-slate-800 text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/50">
            <option value="any">🎯 any (agent tiếp theo)</option>
            <option value="pm">📋 pm</option>
            <option value="analyser">🔍 analyser</option>
            <option value="engineer">⚙️ engineer</option>
            <option value="qa">✅ qa</option>
            <option value="reviewer">🔎 reviewer</option>
            <option value="task_decompose">🗂 task_decompose</option>
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide block mb-1.5">Message</label>
          <textarea value={msg} onChange={(e) => setMsg(e.target.value)} rows={4}
            placeholder="VD: 'Dùng PostgreSQL thay SQLite' hoặc 'Thêm rate limiting vào tất cả endpoints'"
            className="w-full text-sm px-3 py-2 rounded-xl border border-slate-700 bg-slate-800 text-slate-300 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 resize-none" />
        </div>
        <button onClick={send} disabled={sending || !msg.trim()}
          className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-colors disabled:opacity-40 flex items-center justify-center gap-2">
          {sent ? "✓ Đã gửi!" : sending ? <><Spinner />Đang gửi…</> : "📨 Gửi vào Pipeline"}
        </button>
      </div>
      {queue.length > 0 && (
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Đang chờ xử lý ({queue.length})</p>
          <div className="space-y-2">
            {queue.map((m, i) => (
              <div key={i} className="rounded-xl border border-slate-700 bg-slate-800/60 px-3 py-2">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-mono text-indigo-400">→ {m.target_agent}</span>
                  <span className="text-[10px] text-slate-600 ml-auto">{new Date(m.timestamp).toLocaleTimeString()}</span>
                </div>
                <p className="text-xs text-slate-300">{m.from_user}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Spinner ───────────────────────────────────────────────────────────────────

function Spinner() {
  return <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />;
}

// ── Empty card ────────────────────────────────────────────────────────────────

function EmptyCard({ icon, title, sub }: { icon: string; title: string; sub?: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-center py-12">
      <div className="w-16 h-16 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-3xl">{icon}</div>
      <div>
        <p className="text-sm font-semibold text-slate-400">{title}</p>
        {sub && <p className="text-xs text-slate-600 mt-1">{sub}</p>}
      </div>
    </div>
  );
}

// ── Clarification modal ───────────────────────────────────────────────────────

function ClarificationModal({ questions, onSubmit, loading }: {
  questions: string[]; onSubmit: (text: string) => void; loading: boolean;
}) {
  const [text, setText] = useState("");
  return (
    <div className="shrink-0 border-t border-violet-500/30 bg-[#1a1040] px-6 py-5">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xl">❓</span>
          <div>
            <p className="font-bold text-violet-300 text-sm">PM cần làm rõ yêu cầu</p>
            <p className="text-xs text-violet-400/70 mt-0.5">Vui lòng trả lời để pipeline có thể tiếp tục</p>
          </div>
        </div>
        <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 p-3 mb-3">
          {questions.map((q, i) => (
            <p key={i} className="text-sm text-violet-200 flex gap-2 mb-1">
              <span className="font-bold text-violet-400 shrink-0">{i + 1}.</span>{q}
            </p>
          ))}
        </div>
        <div className="flex gap-3">
          <textarea value={text} onChange={(e) => setText(e.target.value)}
            placeholder="Nhập câu trả lời của bạn…"
            rows={2}
            className="flex-1 text-sm px-3 py-2 rounded-xl border border-violet-500/30 bg-slate-800 text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-violet-500/50 resize-none" />
          <button
            onClick={() => { if (text.trim()) onSubmit(text.trim()); }}
            disabled={loading || !text.trim()}
            className="px-5 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold transition-colors disabled:opacity-40 flex items-center gap-2 shrink-0">
            {loading ? <><Spinner />Gửi…</> : "Gửi →"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Approval modal ────────────────────────────────────────────────────────────

function ApprovalModal({ onApprove, onReject, loading }: {
  onApprove: () => void; onReject: () => void; loading: boolean;
}) {
  return (
    <div className="shrink-0 border-t border-amber-500/30 bg-[#1a1200] px-6 py-4">
      <div className="max-w-3xl mx-auto flex items-center gap-4">
        <div className="flex-1">
          <p className="font-bold text-amber-300 text-sm flex items-center gap-2"><span>⏸</span> Spec sẵn sàng — cần duyệt trước khi Engineer bắt đầu</p>
          <p className="text-xs text-amber-400/70 mt-0.5">Xem tab <strong>Spec</strong> để review. Approve → Engineer → Code Review → Security → QA → Deploy.</p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button onClick={onReject} disabled={loading}
            className="px-4 py-2 rounded-xl border border-red-500/40 text-red-400 text-sm font-semibold hover:bg-red-500/10 transition-colors disabled:opacity-40">
            ✗ Từ chối
          </button>
          <button onClick={onApprove} disabled={loading}
            className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold transition-colors disabled:opacity-40 flex items-center gap-2 shadow-lg shadow-emerald-500/20">
            {loading ? <><Spinner />Đang duyệt…</> : "✓ Duyệt — Bắt đầu Engineering"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main tabs ─────────────────────────────────────────────────────────────────

type MainTab = "live" | "plan" | "spec" | "code" | "quality" | "outcome";

const TAB_DEFS: { key: MainTab; label: string; icon: string }[] = [
  { key: "live",    label: "Live",    icon: "📡" },
  { key: "plan",    label: "Plan",    icon: "📋" },
  { key: "spec",    label: "Spec",    icon: "📄" },
  { key: "code",    label: "Code",    icon: "💻" },
  { key: "quality", label: "Quality", icon: "🛡" },
  { key: "outcome", label: "Outcome", icon: "🚀" },
];

function TabBar({ active, setActive, badges }: {
  active: MainTab;
  setActive: (t: MainTab) => void;
  badges: Partial<Record<MainTab, string>>;
}) {
  return (
    <div className="flex border-b border-slate-700/60 bg-slate-900/80 px-4 shrink-0">
      {TAB_DEFS.map(({ key, label, icon }) => (
        <button key={key} onClick={() => setActive(key)}
          className={`relative flex items-center gap-1.5 px-4 py-3 text-xs font-semibold transition-colors border-b-2 whitespace-nowrap
            ${active === key
              ? "border-indigo-400 text-indigo-300"
              : "border-transparent text-slate-500 hover:text-slate-300"}`}>
          <span>{icon}</span>
          <span>{label}</span>
          {badges[key] && (
            <span className={`absolute -top-0.5 -right-0.5 min-w-[1.1rem] h-4 px-1 rounded-full text-[9px] font-bold flex items-center justify-center
              ${badges[key] === "!" || badges[key] === "✗" ? "bg-red-500 text-white"
              : badges[key] === "✓"                        ? "bg-emerald-500 text-white"
              : badges[key] === "⚠"                        ? "bg-amber-400 text-slate-900"
              :                                               "bg-indigo-500 text-white"}`}>
              {badges[key]}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

// ── Sub-tab (within a main tab) ────────────────────────────────────────────────

type SubTab = "tasks" | "sdd" | "analysis" | "review_spec" | "code_review" | "artifacts" | "security" | "qa" | "deploy" | "retro" | "inject";

// ── Root app ──────────────────────────────────────────────────────────────────

export default function App() {
  const pipeline = usePipeline();
  const { status, jobId, jobData, sseEvents, error, approve, reject, rerunFromCheckpoint } = pipeline;

  const [mainTab, setMainTab] = useState<MainTab>("live");
  const [subTab, setSubTab] = useState<SubTab>("tasks");
  const [approveLoading, setApproveLoading] = useState(false);
  const [clarifyLoading, setClarifyLoading] = useState(false);
  const [cancelPending, setCancelPending] = useState(false);
  const [loadJobId, setLoadJobId] = useState("");
  const [archiveMode, setArchiveMode] = useState(false);

  // Auto-switch main tab based on state
  useEffect(() => {
    if (status === "waiting_clarification" || status === "starting") return;
    if (status === "waiting_approval") { setMainTab("spec"); setSubTab("review_spec"); }
    else if (jobData?.spec_analysis && !jobData.spec_analysis.approved) { setMainTab("spec"); setSubTab("analysis"); }
    else if (jobData?.code_review_report) { setMainTab("code"); setSubTab("code_review"); }
    else if (jobData?.security_report) { setMainTab("quality"); setSubTab("security"); }
    else if (jobData?.test_report) { setMainTab("quality"); setSubTab("qa"); }
    else if (jobData?.deploy_report) { setMainTab("outcome"); setSubTab("deploy"); }
    else if (jobData?.retrospective) { setMainTab("outcome"); setSubTab("retro"); }
    else if (jobData?.spec_md || jobData?.plan_md) { setMainTab("plan"); setSubTab("sdd"); }
  }, [
    status,
    !!jobData?.spec_analysis,
    !!jobData?.code_review_report,
    !!jobData?.security_report,
    !!jobData?.test_report,
    !!jobData?.deploy_report,
    !!jobData?.retrospective,
    !!(jobData?.spec_md || jobData?.plan_md),
  ]);

  const handleApprove = useCallback(async () => {
    setApproveLoading(true);
    try { await approve(); } finally { setApproveLoading(false); }
  }, [approve]);

  const handleClarify = useCallback(async (text: string) => {
    setClarifyLoading(true);
    try { await pipeline.clarify(text); } finally { setClarifyLoading(false); }
  }, [pipeline]);

  const handleCancel = useCallback(async () => {
    if (!window.confirm("Huỷ pipeline này?")) return;
    setCancelPending(true);
    try { await pipeline.cancel(); } finally { setCancelPending(false); }
  }, [pipeline]);

  const handleLoadRun = useCallback((runJobId: string) => {
    pipeline.resume(runJobId);
    setArchiveMode(true);
  }, [pipeline]);

  const isActive = status !== "idle";

  // Badges for tab bar
  const badges: Partial<Record<MainTab, string>> = {
    plan:    jobData?.tasks?.length ? String(jobData.tasks.length) : undefined,
    spec:    status === "waiting_approval" ? "!" : jobData?.spec_analysis?.approved === false ? "!" : undefined,
    code:    jobData?.code_review_report?.status === "fail" ? "!" : Object.keys(jobData?.artifact_paths ?? {}).length > 0 ? "✓" : undefined,
    quality: jobData?.security_report?.status === "fail" ? "!" : jobData?.test_report ? (jobData.test_report.status === "pass" ? "✓" : "✗") : undefined,
    outcome: jobData?.deploy_report?.status === "pass" ? "✓" : jobData?.deploy_report?.status === "fail" ? "✗" : undefined,
  };

  return (
    <div className="flex flex-col h-screen bg-slate-900 text-slate-200 overflow-hidden">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="shrink-0 bg-slate-950 border-b border-slate-800 px-4 py-2 flex items-center gap-3">
        <div className="flex items-center gap-2.5 shrink-0">
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center text-sm">🤖</div>
          <span className="font-bold text-sm text-slate-100 hidden sm:block">AI Orchestrator</span>
        </div>
        <div className="h-4 w-px bg-slate-800 shrink-0" />
        {jobId && <CopyButton text={jobId} />}
        {archiveMode && (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/20">
            📚 Archive View
            <button onClick={() => setArchiveMode(false)} className="ml-1 hover:text-white transition-colors">✕</button>
          </span>
        )}
        <div className="flex-1 min-w-0 overflow-hidden mx-2">
          {isActive
            ? <PipelineBar status={status} currentNode={jobData?.current_node ?? null} />
            : <p className="text-xs text-slate-600 text-center">AI Orchestrator — Hệ thống tự động hoá phát triển phần mềm</p>
          }
        </div>
        <StatusBadge status={status} />
      </header>

      {/* ── Body ───────────────────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0">

        {/* ── Left sidebar ─────────────────────────────────────────────── */}
        <aside className="w-64 shrink-0 bg-slate-950 border-r border-slate-800 flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto p-3 space-y-4">

            {/* Pipeline control */}
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-600 mb-2 px-1">
                {isActive ? "Pipeline Control" : "Bắt đầu Pipeline"}
              </p>
              <PipelineForm
                status={status}
                onStart={pipeline.start}
                onCancel={handleCancel}
                onReset={pipeline.reset}
                cancelPending={cancelPending}
              />
            </div>

            {/* Active job info */}
            {jobData && (
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600">Current Job</span>
                  <IntentBadge intent={jobData.pipeline_intent} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { label: "Iteration",     value: jobData.iteration,           highlight: jobData.iteration > 0        },
                    { label: "QA→Analyser",   value: jobData.qa_analyser_iteration, highlight: jobData.qa_analyser_iteration > 0 },
                    { label: "Agents ran",    value: jobData.history.length,       highlight: false },
                    { label: "Spec revisions",value: jobData.spec_revision_count,  highlight: jobData.spec_revision_count > 0 },
                  ].map(({ label, value, highlight }) => (
                    <div key={label} className="rounded-lg bg-slate-800/60 border border-slate-700 px-2 py-2 text-center">
                      <p className="text-[10px] text-slate-600 uppercase tracking-wide">{label}</p>
                      <p className={`text-lg font-bold ${highlight ? "text-amber-400" : "text-slate-300"}`}>{value}</p>
                    </div>
                  ))}
                </div>
                {jobData.project_dir && (
                  <div className="rounded-lg bg-slate-800 border border-slate-700 px-2 py-2">
                    <p className="text-[10px] text-slate-600 mb-0.5">Project</p>
                    <p className="text-xs font-mono text-indigo-400 break-all leading-relaxed">{jobData.project_dir}</p>
                  </div>
                )}
                {/* Action buttons */}
                {status === "done" && (
                  <button onClick={rerunFromCheckpoint}
                    className="w-full text-xs py-1.5 rounded-lg border border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/10 transition-colors">
                    ↺ Resume từ Checkpoint
                  </button>
                )}
                {status === "failed" && error && (
                  <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-2 py-2">
                    <p className="text-[10px] text-red-400 font-mono break-all">{error}</p>
                  </div>
                )}
              </div>
            )}

            {/* Resume job input (idle only) */}
            {status === "idle" && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-600 mb-2 px-1">Resume Job</p>
                <div className="flex flex-col gap-1.5">
                  <input
                    type="text"
                    value={loadJobId}
                    onChange={(e) => setLoadJobId(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && loadJobId.trim()) {
                        pipeline.resume(loadJobId.trim());
                        setLoadJobId("");
                      }
                    }}
                    placeholder="Dán Job ID…"
                    className="w-full text-xs px-3 py-2 rounded-xl border border-slate-700 bg-slate-800 text-slate-300 placeholder-slate-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  />
                  <button
                    disabled={!loadJobId.trim()}
                    onClick={() => { pipeline.resume(loadJobId.trim()); setLoadJobId(""); }}
                    className="w-full text-xs py-1.5 rounded-xl bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors disabled:opacity-40 font-semibold"
                  >
                    Tải Job
                  </button>
                </div>
              </div>
            )}

            {/* Projects browser */}
            <div className="border-t border-slate-800 pt-3">
              <ProjectsBrowser onLoadRun={handleLoadRun} />
            </div>
          </div>
        </aside>

        {/* ── Main content ──────────────────────────────────────────────── */}
        <div className="flex flex-col flex-1 min-w-0 min-h-0">

          <TabBar active={mainTab} setActive={setMainTab} badges={badges} />

          <div className="flex flex-1 min-h-0">

            {/* Tab content */}
            <div className="flex-1 overflow-y-auto p-4 min-h-0">

              {/* LIVE tab */}
              {mainTab === "live" && (
                <div className="h-full">
                  {sseEvents.length === 0 && status === "idle" ? (
                    <div className="flex flex-col items-center justify-center h-full gap-6">
                      <div className="text-center max-w-md">
                        <div className="w-20 h-20 rounded-3xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-4xl mx-auto mb-4">🤖</div>
                        <h2 className="text-xl font-bold text-slate-200 mb-2">AI Orchestrator</h2>
                        <p className="text-sm text-slate-400 mb-6">Hệ thống tự động hoá phát triển phần mềm end-to-end với 10 agent AI chuyên biệt</p>
                        <div className="grid grid-cols-2 gap-2 text-left">
                          {[
                            { icon: "📋", label: "PM Agent",       desc: "Phân tích & lên kế hoạch" },
                            { icon: "🔍", label: "Analyser",       desc: "SDD Spec & Architecture" },
                            { icon: "⚙️", label: "Engineer",       desc: "Implement & TDD" },
                            { icon: "🔎", label: "Code Reviewer",  desc: "Review quality & logic" },
                            { icon: "🛡",  label: "Security",       desc: "Bandit & pip-audit scan" },
                            { icon: "✅", label: "QA Agent",       desc: "Test & validate spec" },
                            { icon: "🚀", label: "Deploy",         desc: "Start & smoke test" },
                            { icon: "📊", label: "Retrospective",  desc: "Lessons learned" },
                          ].map(({ icon, label, desc }) => (
                            <div key={label} className="flex items-center gap-2.5 rounded-xl border border-slate-800 bg-slate-800/40 p-2.5">
                              <span className="text-xl shrink-0">{icon}</span>
                              <div>
                                <p className="text-xs font-semibold text-slate-300">{label}</p>
                                <p className="text-[11px] text-slate-600">{desc}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <AgentTimeline
                      history={jobData?.history ?? []}
                      sseEvents={sseEvents}
                      iteration={jobData?.iteration ?? 0}
                      qaAnalyserIteration={jobData?.qa_analyser_iteration ?? 0}
                    />
                  )}
                </div>
              )}

              {/* PLAN tab */}
              {mainTab === "plan" && (
                <div className="space-y-4 h-full">
                  {/* Sub-tabs */}
                  <div className="flex gap-2">
                    {(["tasks", "sdd", "analysis"] as const).map((k) => (
                      <button key={k} onClick={() => setSubTab(k)}
                        className={`text-xs px-3 py-1.5 rounded-lg font-semibold transition-colors
                          ${subTab === k ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}>
                        {k === "tasks" ? "📋 Tasks" : k === "sdd" ? "📄 SDD Artifacts" : "📐 Spec Analysis"}
                      </button>
                    ))}
                  </div>
                  {subTab === "tasks" && (
                    <div>
                      {jobData?.pipeline_intent && jobData.pipeline_intent !== "feature" && (
                        <div className="mb-3 flex items-center gap-2">
                          <span className="text-xs text-slate-500">Pipeline mode:</span>
                          <IntentBadge intent={jobData.pipeline_intent} />
                        </div>
                      )}
                      <SprintBoard tasks={jobData?.tasks ?? []} dod={jobData?.definition_of_done ?? []} />
                    </div>
                  )}
                  {subTab === "sdd" && (
                    <div className="h-[calc(100vh-220px)]">
                      <SddPanel
                        specMd={jobData?.spec_md ?? ""}
                        planMd={jobData?.plan_md ?? ""}
                        tasksMd={jobData?.tasks_md ?? ""}
                        constitution={jobData?.constitution ?? ""}
                      />
                    </div>
                  )}
                  {subTab === "analysis" && (
                    jobData?.spec_analysis
                      ? <SpecAnalysisPanel report={jobData.spec_analysis} />
                      : <EmptyCard icon="📐" title="Spec Analysis chưa chạy" sub="SpecAnalyze agent sẽ validate spec sau khi Analyser hoàn thành" />
                  )}
                </div>
              )}

              {/* SPEC tab */}
              {mainTab === "spec" && (
                <div className="space-y-4 h-full">
                  <div className="flex gap-2">
                    {(["review_spec", "analysis"] as const).map((k) => (
                      <button key={k} onClick={() => setSubTab(k)}
                        className={`text-xs px-3 py-1.5 rounded-lg font-semibold transition-colors
                          ${subTab === k ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}>
                        {k === "review_spec" ? "📄 Technical Spec" : "📐 Spec Analysis"}
                      </button>
                    ))}
                  </div>
                  {subTab === "review_spec" && (
                    jobData?.spec
                      ? <SpecReview spec={jobData.spec} onApprove={approve} onReject={reject} showButtons={false} />
                      : <EmptyCard icon="📄" title="Technical Spec chưa được tạo" sub={status === "idle" ? "Bắt đầu pipeline để xem spec" : "Analyser đang viết spec…"} />
                  )}
                  {subTab === "analysis" && (
                    jobData?.spec_analysis
                      ? <SpecAnalysisPanel report={jobData.spec_analysis} />
                      : <EmptyCard icon="📐" title="Spec Analysis chưa chạy" />
                  )}
                </div>
              )}

              {/* CODE tab */}
              {mainTab === "code" && (
                <div className="space-y-4 h-full">
                  <div className="flex gap-2">
                    {(["artifacts", "code_review"] as const).map((k) => (
                      <button key={k} onClick={() => setSubTab(k)}
                        className={`text-xs px-3 py-1.5 rounded-lg font-semibold transition-colors
                          ${subTab === k ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}>
                        {k === "artifacts" ? "📁 Artifacts" : "🔎 Code Review"}
                      </button>
                    ))}
                  </div>
                  {subTab === "artifacts" && (
                    <ArtifactList
                      artifactPaths={jobData?.artifact_paths ?? {}}
                      specDir={jobData?.spec_dir}
                      projectDir={jobData?.project_dir}
                    />
                  )}
                  {subTab === "code_review" && (
                    jobData?.code_review_report
                      ? <CodeReviewPanel report={jobData.code_review_report} />
                      : <EmptyCard icon="🔎" title="Code Review chưa chạy" sub="Code Reviewer agent sẽ chạy sau Engineer" />
                  )}
                </div>
              )}

              {/* QUALITY tab */}
              {mainTab === "quality" && (
                <div className="space-y-4 h-full">
                  <div className="flex gap-2">
                    {(["security", "qa", "inject"] as const).map((k) => (
                      <button key={k} onClick={() => setSubTab(k)}
                        className={`text-xs px-3 py-1.5 rounded-lg font-semibold transition-colors
                          ${subTab === k ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}>
                        {k === "security" ? "🛡 Security" : k === "qa" ? "✅ QA Report" : "💬 Inject Message"}
                      </button>
                    ))}
                  </div>
                  {subTab === "security" && (
                    jobData?.security_report
                      ? <SecurityPanel report={jobData.security_report} />
                      : <EmptyCard icon="🛡" title="Security Scan chưa chạy" sub="Security agent sẽ chạy bandit + pip-audit sau Code Review" />
                  )}
                  {subTab === "qa" && (
                    jobData?.test_report
                      ? <TestReport report={jobData.test_report} />
                      : <EmptyCard icon="✅" title="QA Report chưa có" sub="QA agent sẽ validate implementation sau Security" />
                  )}
                  {subTab === "inject" && jobData?.job_id && (
                    <InjectPanel jobId={jobData.job_id} queue={jobData?.user_message_queue ?? []} />
                  )}
                  {subTab === "inject" && !jobData?.job_id && (
                    <EmptyCard icon="💬" title="Chưa có pipeline nào đang chạy" />
                  )}
                </div>
              )}

              {/* OUTCOME tab */}
              {mainTab === "outcome" && (
                <div className="space-y-4 h-full">
                  <div className="flex gap-2">
                    {(["deploy", "retro"] as const).map((k) => (
                      <button key={k} onClick={() => setSubTab(k)}
                        className={`text-xs px-3 py-1.5 rounded-lg font-semibold transition-colors
                          ${subTab === k ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}>
                        {k === "deploy" ? "🚀 Deploy" : "📊 Retrospective"}
                      </button>
                    ))}
                  </div>
                  {subTab === "deploy" && (
                    jobData?.deploy_report
                      ? <DeployPanel report={jobData.deploy_report} />
                      : <EmptyCard icon="🚀" title="Deploy Report chưa có" sub="Deploy agent sẽ chạy sau QA" />
                  )}
                  {subTab === "retro" && (
                    jobData?.retrospective
                      ? <RetroPanel retro={jobData.retrospective} />
                      : <EmptyCard icon="📊" title="Retrospective chưa có" sub="Retrospective agent luôn chạy ở bước cuối cùng" />
                  )}
                </div>
              )}
            </div>
          </div>

          {/* ── Action banners (sticky bottom) ─────────────────────────── */}
          {status === "waiting_clarification" && (
            <ClarificationModal
              questions={jobData?.clarification_questions ?? []}
              onSubmit={handleClarify}
              loading={clarifyLoading}
            />
          )}
          {status === "waiting_approval" && (
            <ApprovalModal onApprove={handleApprove} onReject={reject} loading={approveLoading} />
          )}
        </div>
      </div>
    </div>
  );
}
