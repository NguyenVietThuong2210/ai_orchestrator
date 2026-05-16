import type { PipelineStatus } from "../types";

const CONFIG: Record<PipelineStatus, { label: string; classes: string; dot: string }> = {
  idle:             { label: "Idle",             classes: "bg-gray-100 text-gray-600",    dot: "bg-gray-400" },
  starting:         { label: "Starting…",        classes: "bg-blue-50 text-blue-700",     dot: "bg-blue-500 animate-pulse" },
  running:          { label: "Running",          classes: "bg-blue-50 text-blue-700",     dot: "bg-blue-500 animate-pulse" },
  waiting_approval:      { label: "Awaiting Approval",      classes: "bg-amber-50 text-amber-700",  dot: "bg-amber-500 animate-pulse" },
  waiting_clarification: { label: "Awaiting Clarification", classes: "bg-purple-50 text-purple-700", dot: "bg-purple-500 animate-pulse" },
  done:             { label: "Done",             classes: "bg-green-50 text-green-700",   dot: "bg-green-500" },
  failed:           { label: "Failed",           classes: "bg-red-50 text-red-700",       dot: "bg-red-500" },
};

interface Props {
  status: PipelineStatus;
}

export function StatusBadge({ status }: Props) {
  const { label, classes, dot } = CONFIG[status];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${classes}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  );
}
