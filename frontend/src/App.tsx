import { useState, useEffect, useCallback } from "react";
import { usePipeline } from "./hooks/usePipeline";
import { AgentTimeline } from "./components/AgentTimeline";
import { SpecReview } from "./components/SpecReview";
import { ArtifactList } from "./components/ArtifactList";
import { TestReport } from "./components/TestReport";
import { PipelineForm } from "./components/PipelineForm";
import type { PipelineStatus, Task } from "./types";

// ── Step definitions ──────────────────────────────────────────────────────────

const STEPS = [
  { key: "pm",       label: "PM",       icon: "📋" },
  { key: "analyser", label: "Analyser", icon: "🔍" },
  { key: "gate",     label: "Review",   icon: "👤" },
  { key: "engineer", label: "Engineer", icon: "⚙️"  },
  { key: "qa",       label: "QA",       icon: "✅" },
] as const;

const NODE_TO_STEP: Record<string, string> = {
  pm: "pm", analyser: "analyser", human_gate: "gate", engineer: "engineer", qa: "qa",
};

const STEP_ORDER = ["pm", "analyser", "gate", "engineer", "qa"];

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
    status === "starting"         ? "pm"
    : status === "waiting_approval" ? "gate"
    : currentNode                   ? NODE_TO_STEP[currentNode] ?? null
    : null;
  const aIdx = active ? STEP_ORDER.indexOf(active) : -1;
  if (aIdx > idx) return "done";
  if (aIdx === idx) return "active";
  return "pending";
}

// ── Pipeline flow bar ─────────────────────────────────────────────────────────

function PipelineFlowBar({ status, currentNode }: { status: PipelineStatus; currentNode: string | null }) {
  return (
    <div className="flex items-center w-full">
      {STEPS.map(({ key, label, icon }, i) => {
        const s = getStepState(key, status, currentNode);
        const isLast = i === STEPS.length - 1;
        return (
          <div key={key} className="flex items-center flex-1 min-w-0">
            <div className="flex flex-col items-center flex-1 min-w-0">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm border-2 transition-all
                ${s === "done"   ? "bg-green-500 border-green-500 text-white shadow"
                : s === "active" ? "bg-blue-500 border-blue-400 text-white shadow-lg ring-4 ring-blue-200 animate-pulse"
                : s === "error"  ? "bg-red-500 border-red-400 text-white"
                :                  "bg-white border-gray-200 text-gray-300"}`}>
                {s === "done" ? "✓" : s === "error" ? "✗" : icon}
              </div>
              <span className={`text-[10px] mt-0.5 font-semibold tracking-wide
                ${s === "done"   ? "text-green-600"
                : s === "active" ? "text-blue-600"
                : s === "error"  ? "text-red-600"
                :                  "text-gray-400"}`}>
                {label}
              </span>
            </div>
            {!isLast && (
              <div className={`h-0.5 w-3 mx-0.5 rounded shrink-0
                ${getStepState(STEPS[i + 1].key, status, currentNode) !== "pending" || s === "done"
                  ? "bg-green-400" : "bg-gray-200"}`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Status pill ───────────────────────────────────────────────────────────────

function StatusPill({ status }: { status: PipelineStatus }) {
  const cfg: Record<PipelineStatus, { label: string; cls: string }> = {
    idle:             { label: "Idle",           cls: "bg-gray-700 text-gray-300" },
    starting:         { label: "Starting…",      cls: "bg-blue-600 text-white animate-pulse" },
    running:          { label: "● Running",      cls: "bg-blue-500 text-white" },
    waiting_approval: { label: "⏸ Needs Review", cls: "bg-amber-400 text-amber-900 animate-pulse" },
    done:             { label: "✓ Done",         cls: "bg-green-500 text-white" },
    failed:           { label: "✗ Failed",       cls: "bg-red-500 text-white" },
  };
  const { label, cls } = cfg[status];
  return <span className={`px-3 py-1 rounded-full text-xs font-bold ${cls}`}>{label}</span>;
}

// ── Copy-to-clipboard button ──────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }, [text]);
  return (
    <button
      onClick={copy}
      title="Copy job ID"
      className="text-xs text-gray-500 hover:text-white transition-colors font-mono px-1.5 py-0.5 rounded hover:bg-gray-700"
    >
      {copied ? "✓ copied" : text.slice(0, 8) + "…"}
    </button>
  );
}

// ── Approve banner ────────────────────────────────────────────────────────────

function ApprovalBanner({ onApprove, onReject, loading }: {
  onApprove: () => void; onReject: () => void; loading: boolean;
}) {
  return (
    <div className="shrink-0 bg-amber-50 border-t-2 border-amber-300 px-6 py-4 shadow-xl">
      <div className="flex items-start gap-3 mb-3">
        <span className="text-2xl shrink-0 mt-0.5">⏸</span>
        <div>
          <p className="font-bold text-amber-900 text-sm">Spec ready — approval required before Engineering starts</p>
          <p className="text-xs text-amber-700 mt-0.5">
            Review the <strong>Spec</strong> tab. Approve to let Engineer write code, or Reject to cancel.
          </p>
        </div>
      </div>
      <div className="flex gap-3 justify-end">
        <button
          onClick={onReject}
          disabled={loading}
          className="px-4 py-2 rounded-lg border-2 border-red-300 text-red-700 text-sm font-semibold hover:bg-red-50 transition-colors disabled:opacity-40"
        >
          ✗ Reject &amp; Cancel
        </button>
        <button
          onClick={onApprove}
          disabled={loading}
          className="px-6 py-2 rounded-lg bg-green-600 text-white text-sm font-bold hover:bg-green-700 transition-colors shadow disabled:opacity-60 flex items-center gap-2"
        >
          {loading
            ? <><span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" /> Approving…</>
            : "✓ Approve — Start Engineering"}
        </button>
      </div>
    </div>
  );
}

// ── Sprint Board (Tasks tab) ──────────────────────────────────────────────────

const STATUS_DOT: Record<string, string> = {
  done:        "bg-green-500",
  in_progress: "bg-blue-500 animate-pulse",
  pending:     "bg-gray-300",
};

const STATUS_LABEL: Record<string, { label: string; cls: string }> = {
  done:        { label: "Done",        cls: "bg-green-100 text-green-700" },
  in_progress: { label: "In Progress", cls: "bg-blue-100 text-blue-700" },
  pending:     { label: "To Do",       cls: "bg-gray-100 text-gray-500" },
};

const PRIORITY_CFG: Record<number, { label: string; cls: string; border: string }> = {
  1: { label: "P1 · Critical", cls: "text-red-600 bg-red-50",    border: "border-l-red-400" },
  2: { label: "P2 · High",     cls: "text-amber-600 bg-amber-50", border: "border-l-amber-400" },
  3: { label: "P3 · Medium",   cls: "text-blue-600 bg-blue-50",   border: "border-l-blue-300" },
};

function SprintBoard({ tasks }: { tasks: Task[] }) {
  if (!tasks.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-gray-400">
        <span className="text-4xl">📋</span>
        <p className="text-sm">PM hasn't produced tasks yet.</p>
        <p className="text-xs opacity-70">Tasks appear here after the PM agent completes.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-gray-700">Sprint Board</h2>
        <div className="flex gap-2 text-[10px]">
          <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
            {tasks.filter((t) => t.status === "done").length}/{tasks.length} done
          </span>
          {tasks.filter((t) => t.status === "in_progress").length > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-600">
              {tasks.filter((t) => t.status === "in_progress").length} in progress
            </span>
          )}
        </div>
      </div>

      {tasks.map((t) => {
        const pCfg = PRIORITY_CFG[t.priority] ?? PRIORITY_CFG[3];
        const sCfg = STATUS_LABEL[t.status] ?? STATUS_LABEL["pending"];
        return (
          <div key={t.id} className={`rounded-lg bg-white border border-gray-200 border-l-4 ${pCfg.border} p-4 shadow-sm`}>
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${pCfg.cls}`}>{pCfg.label}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${sCfg.cls} flex items-center gap-1`}>
                  <span className={`w-1.5 h-1.5 rounded-full inline-block ${STATUS_DOT[t.status] ?? "bg-gray-300"}`} />
                  {sCfg.label}
                </span>
              </div>
              <span className="text-[10px] font-mono text-gray-400 shrink-0">{t.id}</span>
            </div>
            <p className="text-sm font-semibold text-gray-800 mb-1 leading-snug">{t.title}</p>
            {t.description && (
              <p className="text-xs text-gray-600 leading-relaxed">{t.description}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Stat tile ─────────────────────────────────────────────────────────────────

function StatTile({ label, value, color = "text-gray-700" }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="rounded-lg bg-gray-50 border border-gray-100 px-3 py-2 text-center">
      <p className="text-[10px] text-gray-400 uppercase tracking-wide">{label}</p>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
    </div>
  );
}

// ── Right panel ───────────────────────────────────────────────────────────────

type RightTab = "tasks" | "spec" | "code" | "qa";

function RightPanel({
  pipeline,
  activeTab,
  setActiveTab,
  approveLoading,
}: {
  pipeline: ReturnType<typeof usePipeline>;
  activeTab: RightTab;
  setActiveTab: (t: RightTab) => void;
  approveLoading: boolean;
}) {
  const { status, jobData, approve, reject } = pipeline;
  const hasTasks     = (jobData?.tasks?.length ?? 0) > 0;
  const hasSpec      = !!jobData?.spec;
  const hasQA        = !!jobData?.test_report;
  const hasCode      = Object.keys(jobData?.artifact_paths ?? {}).length > 0 || !!jobData?.spec_dir;

  const tabs: { key: RightTab; label: string; badge?: string; enabled: boolean }[] = [
    {
      key: "tasks",
      label: "Tasks",
      badge: hasTasks ? String(jobData!.tasks.length) : undefined,
      enabled: true,
    },
    {
      key: "spec",
      label: "Spec",
      badge: status === "waiting_approval" ? "!" : undefined,
      enabled: true,
    },
    {
      key: "code",
      label: "Code",
      badge: Object.keys(jobData?.artifact_paths ?? {}).length > 0
        ? String(Object.keys(jobData!.artifact_paths).length)
        : undefined,
      enabled: hasCode,
    },
    {
      key: "qa",
      label: "QA Report",
      badge: jobData?.test_report ? (jobData.test_report.status === "pass" ? "✓" : "✗") : undefined,
      enabled: hasQA,
    },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex gap-0.5 px-3 pt-2 shrink-0 border-b border-gray-100 bg-white">
        {tabs.map(({ key, label, badge, enabled }) => (
          <button
            key={key}
            disabled={!enabled}
            onClick={() => setActiveTab(key)}
            className={`relative px-3 py-2 text-xs font-semibold rounded-t transition-colors border-b-2
              ${activeTab === key
                ? "border-blue-500 text-blue-700 bg-blue-50/50"
                : enabled
                ? "border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                : "border-transparent text-gray-300 cursor-not-allowed"}`}
          >
            {label}
            {badge && (
              <span className={`absolute -top-1 -right-1 min-w-[1rem] h-4 px-0.5 rounded-full text-[9px] flex items-center justify-center font-bold
                ${badge === "!" ? "bg-amber-400 text-amber-900"
                : badge === "✓" ? "bg-green-500 text-white"
                : badge === "✗" ? "bg-red-500 text-white"
                : "bg-blue-500 text-white"}`}>
                {badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4 min-h-0">
        {activeTab === "tasks" && (
          <SprintBoard tasks={jobData?.tasks ?? []} />
        )}

        {activeTab === "spec" && (
          hasSpec
            ? <SpecReview spec={jobData!.spec!} onApprove={approve} onReject={reject} showButtons={false} />
            : (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-gray-400">
                <span className="text-4xl">🔍</span>
                {status === "idle"
                  ? <p className="text-sm">Start a pipeline to see the technical spec here.</p>
                  : <><div className="w-8 h-8 border-2 border-gray-200 border-t-blue-400 rounded-full animate-spin" />
                     <p className="text-sm">Analyser is writing the spec…</p></>
                }
              </div>
            )
        )}

        {activeTab === "code" && (
          <ArtifactList
            artifactPaths={jobData?.artifact_paths ?? {}}
            specDir={jobData?.spec_dir}
            projectDir={jobData?.project_dir}
          />
        )}

        {activeTab === "qa" && (
          hasQA
            ? <TestReport report={jobData!.test_report!} />
            : <div className="flex flex-col items-center justify-center h-full gap-3 text-gray-400">
                <span className="text-4xl">✅</span>
                <p className="text-sm">QA report not yet available.</p>
              </div>
        )}
      </div>

      {/* Sticky approval banner */}
      {status === "waiting_approval" && (
        <ApprovalBanner onApprove={approve} onReject={reject} loading={approveLoading} />
      )}
    </div>
  );
}

// ── Root app ──────────────────────────────────────────────────────────────────

export default function App() {
  const pipeline = usePipeline();
  const { status, jobId, jobData, sseEvents, error, approve, reject, rerunFromCheckpoint } = pipeline;

  const [rightTab, setRightTab] = useState<RightTab>("tasks");
  const [approveLoading, setApproveLoading] = useState(false);
  const [cancelPending, setCancelPending] = useState(false);
  const [loadJobId, setLoadJobId] = useState("");

  // Auto-switch tabs when pipeline progresses
  useEffect(() => {
    if (status === "waiting_approval") setRightTab("spec");
  }, [status]);

  useEffect(() => {
    if (jobData?.tasks && jobData.tasks.length > 0 && status === "running") {
      setRightTab("tasks");
    }
  }, [jobData?.tasks?.length]);

  useEffect(() => {
    if (status === "done" && jobData?.test_report) setRightTab("qa");
  }, [status, jobData?.test_report]);

  const handleApprove = useCallback(async () => {
    setApproveLoading(true);
    try { await approve(); } finally { setApproveLoading(false); }
  }, [approve]);

  const handleCancel = useCallback(async () => {
    if (!window.confirm("Cancel this pipeline run?")) return;
    setCancelPending(true);
    try { await pipeline.cancel(); } finally { setCancelPending(false); }
  }, [pipeline]);

  const isActive = status !== "idle";

  return (
    <div className="flex flex-col h-screen bg-gray-50 overflow-hidden">

      {/* ── Header ── */}
      <header className="shrink-0 bg-gray-900 text-white px-4 py-2.5 flex items-center gap-4 border-b border-gray-800">
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-lg">🤖</span>
          <span className="font-bold text-sm tracking-tight">AI Orchestrator</span>
        </div>

        {jobId && <CopyButton text={jobId} />}

        <div className="flex-1 max-w-md mx-auto hidden sm:block">
          {isActive
            ? <PipelineFlowBar status={status} currentNode={jobData?.current_node ?? null} />
            : <p className="text-xs text-gray-600 text-center">Start a pipeline to see progress</p>
          }
        </div>

        <StatusPill status={status} />
      </header>

      {/* ── Body ── */}
      <div className="flex flex-1 min-h-0">

        {/* Sidebar */}
        <aside className="w-56 shrink-0 bg-white border-r border-gray-100 flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto p-3 space-y-4">

            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-2">
                {isActive ? "Pipeline Control" : "New Pipeline"}
              </p>
              <PipelineForm
                status={status}
                onStart={pipeline.start}
                onCancel={handleCancel}
                onReset={pipeline.reset}
                cancelPending={cancelPending}
              />
            </div>

            {/* Resume existing job — shown only when idle */}
            {status === "idle" && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-2">
                  Resume Existing Job
                </p>
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
                    placeholder="Paste job ID…"
                    className="w-full text-xs px-2.5 py-1.5 border border-gray-200 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-blue-300 placeholder-gray-300"
                  />
                  <button
                    disabled={!loadJobId.trim()}
                    onClick={() => { pipeline.resume(loadJobId.trim()); setLoadJobId(""); }}
                    className="w-full text-xs py-1.5 rounded-lg bg-gray-800 text-white font-semibold hover:bg-gray-700 transition-colors disabled:opacity-40"
                  >
                    Load Job
                  </button>
                </div>
              </div>
            )}

            {/* Project folder path */}
            {jobData?.project_dir && (
              <div className="rounded-lg bg-gray-50 border border-gray-200 px-3 py-2">
                <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1">Project</p>
                <p className="text-[11px] font-mono text-blue-700 break-all">{jobData.project_dir}</p>
              </div>
            )}

            {/* Stats */}
            {jobData && (
              <div className="grid grid-cols-2 gap-2">
                <StatTile
                  label="Eng retry"
                  value={jobData.iteration}
                  color={jobData.iteration > 0 ? "text-amber-600" : "text-gray-700"}
                />
                <StatTile
                  label="Spec retry"
                  value={jobData.qa_analyser_iteration}
                  color={jobData.qa_analyser_iteration > 0 ? "text-amber-600" : "text-gray-700"}
                />
                {jobData.history.length > 0 && (
                  <StatTile label="Agents run" value={jobData.history.length} />
                )}
              </div>
            )}
          </div>

          {error && (
            <div className="shrink-0 p-2 bg-red-50 border-t border-red-100">
              <p className="text-[10px] text-red-700 font-mono break-all">{error}</p>
            </div>
          )}
        </aside>

        {/* Main: timeline + right panel */}
        <div className="flex flex-1 min-w-0 min-h-0">

          {/* Agent timeline */}
          <div className="w-64 shrink-0 border-r border-gray-100 bg-white flex flex-col min-h-0">
            <div className="shrink-0 px-3 py-2 border-b border-gray-100 flex items-center justify-between">
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Agent Activity</p>
              {jobData && (
                <span className="text-[10px] text-gray-400">
                  {jobData.history.length} run{jobData.history.length !== 1 ? "s" : ""}
                </span>
              )}
            </div>
            <div className="flex-1 overflow-y-auto p-2.5">
              {status === "idle"
                ? <p className="text-xs text-gray-300 text-center pt-12">No pipeline running.</p>
                : <AgentTimeline
                    history={jobData?.history ?? []}
                    sseEvents={sseEvents}
                    iteration={jobData?.iteration ?? 0}
                    qaAnalyserIteration={jobData?.qa_analyser_iteration ?? 0}
                  />
              }
            </div>
          </div>

          {/* Right panel: Tasks / Spec / Code / QA */}
          <div className="flex-1 min-w-0 flex flex-col min-h-0">
            {/* Terminal banners */}
            {status === "done" && (
              <div className="shrink-0 mx-4 mt-3 rounded-xl bg-green-50 border border-green-200 px-4 py-2.5 flex items-center gap-3">
                <span className="text-xl">✅</span>
                <p className="text-sm font-semibold text-green-800">
                  Pipeline complete — all tests passed
                  {jobData?.cost_estimate_usd === 0 ? " (Mode B: $0 API cost)" : ""}
                </p>
              </div>
            )}
            {status === "failed" && (
              <div className="shrink-0 mx-4 mt-3 rounded-xl bg-red-50 border border-red-200 px-4 py-2.5 flex items-start gap-3">
                <span className="text-xl shrink-0">❌</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-red-800">Pipeline failed</p>
                  {error && <p className="text-[11px] text-red-600 font-mono mt-0.5 break-all">{error}</p>}
                </div>
                {/* Show re-run button only when LangGraph has a recoverable checkpoint */}
                {jobData?.current_node && !["end", "done", "failed"].includes(jobData.current_node) && (
                  <button
                    onClick={rerunFromCheckpoint}
                    className="shrink-0 px-3 py-1.5 rounded-lg bg-red-700 hover:bg-red-800 text-white text-xs font-bold transition-colors flex items-center gap-1.5"
                    title="Resume from last LangGraph checkpoint — skips already-completed agents"
                  >
                    ↺ Re-run from <span className="font-mono">{jobData.current_node}</span>
                  </button>
                )}
              </div>
            )}

            <div className="flex-1 min-h-0">
              <RightPanel
                pipeline={{ ...pipeline, approve: handleApprove, reject }}
                activeTab={rightTab}
                setActiveTab={setRightTab}
                approveLoading={approveLoading}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
