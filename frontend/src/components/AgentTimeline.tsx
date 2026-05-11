import { useEffect, useRef } from "react";
import type { AgentEvent, SSEEvent } from "../types";

const AGENT_COLOR: Record<string, string> = {
  pm:       "bg-purple-100 text-purple-700 border-purple-200",
  analyser: "bg-blue-100 text-blue-700 border-blue-200",
  engineer: "bg-orange-100 text-orange-700 border-orange-200",
  qa:       "bg-green-100 text-green-700 border-green-200",
};

const STATUS_ICON: Record<string, string> = {
  done:         "✓",
  ok:           "✓",
  running:      "…",
  failed:       "✗",
  pass:         "✓",
  "fail-minor": "⚠",
  "fail-major": "✗",
};

// Only surface meaningful LangGraph events to avoid noise
const SHOW_SSE_EVENTS = new Set([
  "on_chat_model_start",
  "on_chat_model_end",
  "on_tool_start",
  "on_tool_end",
  "on_retriever_start",
  "on_retriever_end",
]);

const SSE_LABEL: Record<string, string> = {
  on_chat_model_start: "🧠 model thinking…",
  on_chat_model_end:   "🧠 model response",
  on_tool_start:       "🔧 tool call",
  on_tool_end:         "🔧 tool done",
  on_retriever_start:  "📚 retriever",
  on_retriever_end:    "📚 retrieved",
};

interface Props {
  history: AgentEvent[];
  sseEvents: SSEEvent[];
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
          <span>{event.tokens_used.toLocaleString()} tok</span>
        )}
        <span className="ml-auto">{new Date(event.timestamp).toLocaleTimeString()}</span>
      </div>
    </div>
  );
}

function SSERow({ e }: { e: SSEEvent }) {
  if (!SHOW_SSE_EVENTS.has(e.event)) return null;
  const label = SSE_LABEL[e.event] ?? e.event;
  const detail = e.name && e.name !== e.event ? e.name : "";
  return (
    <div className="flex items-center gap-2 text-xs font-mono text-gray-500 py-0.5 px-1">
      <span className="opacity-70 shrink-0">{label}</span>
      {detail && (
        <span className="text-gray-400 truncate text-[10px]" title={detail}>
          {detail.length > 30 ? detail.slice(0, 30) + "…" : detail}
        </span>
      )}
    </div>
  );
}

export function AgentTimeline({ history, sseEvents, iteration, qaAnalyserIteration }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history.length, sseEvents.length]);

  const visibleSSE = sseEvents.filter((e) => SHOW_SSE_EVENTS.has(e.event)).slice(-10);

  return (
    <div className="space-y-2">
      {history.length === 0 && sseEvents.length === 0 && (
        <div className="text-sm text-gray-400 text-center py-12">
          Waiting for first agent to start…
        </div>
      )}

      {/* Retry counters — shown only when retries have happened */}
      {(iteration > 0 || qaAnalyserIteration > 0) && (
        <div className="flex gap-2 px-1">
          {iteration > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-mono">
              eng retry {iteration}×
            </span>
          )}
          {qaAnalyserIteration > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-mono">
              spec retry {qaAnalyserIteration}×
            </span>
          )}
        </div>
      )}

      {history.map((event, i) => (
        <AgentCard key={i} event={event} />
      ))}

      {/* Live SSE — only meaningful events, last 10 */}
      {visibleSSE.length > 0 && (
        <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50 px-2 py-1.5 space-y-0.5">
          <p className="text-[9px] uppercase tracking-widest text-gray-400 mb-1 px-1">Live</p>
          {visibleSSE.map((e, i) => (
            <SSERow key={i} e={e} />
          ))}
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
