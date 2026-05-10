import { useEffect, useRef } from "react";
import type { AgentEvent, SSEEvent } from "../types";

const AGENT_COLOR: Record<string, string> = {
  pm:       "bg-purple-100 text-purple-700 border-purple-200",
  analyser: "bg-blue-100 text-blue-700 border-blue-200",
  engineer: "bg-orange-100 text-orange-700 border-orange-200",
  qa:       "bg-green-100 text-green-700 border-green-200",
};

const STATUS_ICON: Record<string, string> = {
  done:       "✓",
  running:    "…",
  failed:     "✗",
  pass:       "✓",
  "fail-minor": "⚠",
  "fail-major": "✗",
};

interface Props {
  history: AgentEvent[];        // authoritative — from polling
  sseEvents: SSEEvent[];        // real-time — from SSE stream
  iteration: number;
  qaAnalyserIteration: number;
}

function AgentCard({ event }: { event: AgentEvent }) {
  const colorClass = AGENT_COLOR[event.agent] ?? "bg-gray-100 text-gray-700 border-gray-200";
  const icon = STATUS_ICON[event.status] ?? "·";

  return (
    <div className={`rounded-lg border p-3 space-y-1 ${colorClass}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono font-semibold text-xs uppercase tracking-wide">
            {event.agent}
          </span>
          <span className="text-xs opacity-70">{event.status}</span>
        </div>
        <span className="text-lg leading-none">{icon}</span>
      </div>
      {event.note && (
        <p className="text-xs opacity-80 font-mono leading-snug">{event.note}</p>
      )}
      <div className="flex gap-3 text-xs opacity-60">
        {event.duration_seconds > 0 && (
          <span>{event.duration_seconds.toFixed(1)}s</span>
        )}
        {event.tokens_used > 0 && (
          <span>{event.tokens_used.toLocaleString()} tokens</span>
        )}
        <span>{new Date(event.timestamp).toLocaleTimeString()}</span>
      </div>
    </div>
  );
}

function SSERow({ e }: { e: SSEEvent }) {
  if (e.event === "on_chain_start" || e.event === "on_chain_end") return null;
  return (
    <div className="flex gap-2 text-xs font-mono text-gray-500 py-0.5 px-1">
      <span className="opacity-50">{e.event}</span>
      {e.name && <span className="text-gray-700">{e.name}</span>}
    </div>
  );
}

export function AgentTimeline({ history, sseEvents }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history.length, sseEvents.length]);

  return (
    <div className="space-y-2">
      {history.length === 0 && sseEvents.length === 0 && (
        <div className="text-sm text-gray-400 text-center py-12">
          Waiting for first agent to start…
        </div>
      )}

      {history.map((event, i) => (
        <AgentCard key={i} event={event} />
      ))}

      {/* Live SSE events */}
      {sseEvents.length > 0 && (
        <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50 px-2 py-1 space-y-0.5">
          {sseEvents.slice(-20).map((e, i) => (
            <SSERow key={i} e={e} />
          ))}
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
