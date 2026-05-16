import type { RunSummary } from "../types";
import { useProjects } from "../hooks/useProjects";

interface Props {
  onLoadRun: (jobId: string) => void;
}

const STATUS_COLORS: Record<string, string> = {
  done:    "text-emerald-400",
  failed:  "text-red-400",
  running: "text-blue-400",
  unknown: "text-slate-400",
};

const STATUS_ICONS: Record<string, string> = {
  done:    "✅",
  failed:  "❌",
  running: "⚙️",
  unknown: "❓",
};

const INTENT_LABELS: Record<string, string> = {
  feature:  "✨ Feature",
  bug_fix:  "🐛 Bug Fix",
  test:     "🧪 Test",
  review:   "🔎 Review",
  query:    "🔍 Query",
};

function formatDate(iso: string): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso.slice(0, 16);
  }
}

function RunRow({ run, onLoad }: { run: RunSummary; onLoad: () => void }) {
  const statusColor = STATUS_COLORS[run.status] ?? STATUS_COLORS.unknown;
  const statusIcon  = STATUS_ICONS[run.status]  ?? STATUS_ICONS.unknown;
  const intentLabel = INTENT_LABELS[run.pipeline_intent] ?? run.pipeline_intent;

  return (
    <div className="flex items-center gap-2 py-1.5 px-3 rounded hover:bg-slate-700/40 group text-sm">
      <span className="text-base" title={run.status}>{statusIcon}</span>
      <span className="text-slate-400 text-xs w-28 shrink-0">{formatDate(run.created_at)}</span>
      <span className="text-indigo-300 text-xs w-24 shrink-0">{intentLabel}</span>
      <span className={`text-xs w-16 shrink-0 font-semibold ${statusColor}`}>{run.status}</span>
      <span className="text-slate-300 truncate flex-1 text-xs" title={run.request_snippet}>
        {run.request_snippet || "(no request)"}
      </span>
      {run.task_count > 0 && (
        <span className="text-slate-500 text-xs shrink-0">{run.task_count} tasks</span>
      )}
      <button
        onClick={onLoad}
        className="opacity-0 group-hover:opacity-100 transition-opacity text-xs px-2 py-0.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded shrink-0"
      >
        Load
      </button>
    </div>
  );
}

export function ProjectsBrowser({ onLoadRun }: Props) {
  const { projects, loading, expandedProject, projectRuns, runsLoading, toggleProject, refresh } = useProjects();

  if (loading && projects.length === 0) {
    return (
      <div className="text-slate-500 text-xs px-2 py-3 text-center">
        Loading projects…
      </div>
    );
  }

  if (!loading && projects.length === 0) {
    return (
      <div className="text-slate-600 text-xs px-2 py-2 text-center italic">
        No project history yet
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center justify-between px-1 mb-1">
        <span className="text-slate-400 text-xs font-semibold uppercase tracking-wide">Projects</span>
        <button
          onClick={refresh}
          className="text-slate-600 hover:text-slate-400 text-xs px-1"
          title="Refresh"
        >
          ↺
        </button>
      </div>

      {projects.map((proj) => {
        const isOpen = expandedProject === proj.project_name;
        const runs   = projectRuns[proj.project_name] ?? [];
        const isLoadingRuns = runsLoading[proj.project_name];
        const statusColor = STATUS_COLORS[proj.status] ?? STATUS_COLORS.unknown;

        return (
          <div key={proj.project_name} className="rounded-md overflow-hidden border border-slate-700/50">
            <button
              onClick={() => toggleProject(proj.project_name)}
              className="w-full flex items-center gap-2 px-2 py-1.5 text-left hover:bg-slate-700/40 transition-colors"
            >
              <span className="text-slate-300 text-sm">🗂</span>
              <span className="text-slate-200 text-xs font-semibold truncate flex-1">
                {proj.project_name}
              </span>
              <span className="text-slate-500 text-xs shrink-0">{proj.run_count} runs</span>
              <span className={`text-xs font-semibold shrink-0 ${statusColor}`}>
                {STATUS_ICONS[proj.status] ?? "❓"}
              </span>
              <span className="text-slate-500 text-xs">{isOpen ? "▲" : "▼"}</span>
            </button>

            {isOpen && (
              <div className="border-t border-slate-700/50 bg-slate-800/30">
                {isLoadingRuns ? (
                  <div className="text-slate-500 text-xs py-2 text-center">Loading…</div>
                ) : runs.length === 0 ? (
                  <div className="text-slate-600 text-xs py-2 text-center italic">No runs found</div>
                ) : (
                  runs.map((run) => (
                    <RunRow
                      key={run.job_id}
                      run={run}
                      onLoad={() => onLoadRun(run.job_id)}
                    />
                  ))
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
