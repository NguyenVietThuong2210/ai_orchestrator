import type { TechnicalSpec } from "../types";

interface Props {
  spec: TechnicalSpec;
  onApprove: () => void;
  onReject: () => void;
  showButtons?: boolean;
}

const SEVERITY_BADGE: Record<string, string> = {
  low:    "bg-gray-100 text-gray-600",
  medium: "bg-amber-100 text-amber-700",
  high:   "bg-red-100 text-red-700",
};

const METHOD_COLOR: Record<string, string> = {
  GET:    "bg-green-100 text-green-700",
  POST:   "bg-blue-100 text-blue-700",
  PUT:    "bg-amber-100 text-amber-700",
  PATCH:  "bg-orange-100 text-orange-700",
  DELETE: "bg-red-100 text-red-700",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 border-b border-gray-100 pb-1">
        {title}
      </h3>
      {children}
    </div>
  );
}

export function SpecReview({ spec, onApprove, onReject, showButtons = true }: Props) {
  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex-1 overflow-y-auto space-y-5 pr-1">

        {/* Overview */}
        <Section title="Overview">
          <p className="text-sm text-gray-700 leading-relaxed">{spec.overview}</p>
        </Section>

        {/* Components */}
        {(spec.components ?? []).length > 0 && (
          <Section title={`Components (${(spec.components ?? []).length})`}>
            <div className="space-y-2">
              {(spec.components ?? []).map((c, i) => (
                <div key={i} className="rounded-lg bg-blue-50 border border-blue-100 p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono font-bold text-xs text-blue-800 bg-blue-100 px-2 py-0.5 rounded">
                      {c.name}
                    </span>
                    {(c.dependencies ?? []).length > 0 && (
                      <span className="text-[10px] text-blue-400">
                        depends on: {c.dependencies!.join(", ")}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-blue-700 leading-snug">
                    {c.responsibility ?? (c as unknown as Record<string, string>).description}
                  </p>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* API Contracts */}
        {(spec.api_contracts ?? []).length > 0 && (
          <Section title={`API Contracts (${(spec.api_contracts ?? []).length})`}>
            <div className="space-y-2">
              {(spec.api_contracts ?? []).map((c, i) => (
                <div key={i} className="rounded-lg border border-gray-200 bg-white p-3">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={`text-xs font-bold px-2 py-0.5 rounded font-mono ${METHOD_COLOR[c.method] ?? "bg-gray-100 text-gray-700"}`}>
                      {c.method}
                    </span>
                    <span className="font-mono text-sm font-semibold text-gray-800">{c.path}</span>
                  </div>
                  {c.description && (
                    <p className="text-xs text-gray-500 mb-1.5">{c.description}</p>
                  )}
                  {c.request_schema && Object.keys(c.request_schema).length > 0 && (
                    <details className="text-xs mt-1">
                      <summary className="text-gray-400 cursor-pointer hover:text-gray-600">Request schema</summary>
                      <pre className="mt-1 bg-gray-50 rounded p-2 text-[11px] overflow-x-auto text-gray-700">
                        {JSON.stringify(c.request_schema, null, 2)}
                      </pre>
                    </details>
                  )}
                  {c.response_schema && Object.keys(c.response_schema).length > 0 && (
                    <details className="text-xs mt-1">
                      <summary className="text-gray-400 cursor-pointer hover:text-gray-600">Response schema</summary>
                      <pre className="mt-1 bg-gray-50 rounded p-2 text-[11px] overflow-x-auto text-gray-700">
                        {JSON.stringify(c.response_schema, null, 2)}
                      </pre>
                    </details>
                  )}
                  {c.response && (
                    <span className="text-xs text-gray-400 mt-1 block">→ {c.response}</span>
                  )}
                  {(c.errors ?? []).length > 0 && (
                    <p className="text-xs text-red-400 mt-1">Errors: {c.errors!.join(", ")}</p>
                  )}
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Data Models */}
        {(spec.data_models ?? []).length > 0 && (
          <Section title={`Data Models (${(spec.data_models ?? []).length})`}>
            <div className="space-y-2">
              {(spec.data_models ?? []).map((m, i) => (
                <div key={i} className="rounded-lg border border-gray-200 bg-white p-3">
                  <p className="font-mono font-bold text-sm text-gray-800 mb-1">{m.name}</p>
                  {m.description && <p className="text-xs text-gray-500 mb-1.5">{m.description}</p>}
                  {(m.fields ?? []).length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {(m.fields ?? []).map((f, fi) => (
                        <span key={fi} className="font-mono text-[11px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                          {typeof f === "string" ? f : (f as Record<string, unknown>).name as string ?? JSON.stringify(f)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Acceptance Criteria */}
        {(spec.acceptance_criteria ?? []).length > 0 && (
          <Section title={`Acceptance Criteria (${(spec.acceptance_criteria ?? []).length})`}>
            <ul className="space-y-1.5">
              {(spec.acceptance_criteria ?? []).map((c, i) => (
                <li key={i} className="flex gap-2 text-sm">
                  <span className="text-green-400 mt-0.5 shrink-0">□</span>
                  <span className="text-gray-700 leading-snug">{c}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {/* Risks */}
        {(spec.risks ?? []).length > 0 && (
          <Section title={`Risks (${(spec.risks ?? []).length})`}>
            <div className="space-y-2">
              {(spec.risks ?? []).map((r, i) => (
                <div key={i} className="rounded-lg border border-amber-100 bg-amber-50 p-3">
                  <div className="flex items-start gap-2">
                    <span className="text-amber-500 mt-0.5 shrink-0">⚠</span>
                    <div>
                      <div className="flex items-center gap-2 mb-0.5">
                        <p className="text-sm text-amber-900 font-medium">{r.description}</p>
                        {r.severity && (
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${SEVERITY_BADGE[r.severity] ?? "bg-gray-100 text-gray-600"}`}>
                            {r.severity}
                          </span>
                        )}
                      </div>
                      {r.mitigation && (
                        <p className="text-xs text-amber-700 leading-snug">
                          <span className="font-semibold">Mitigation:</span> {r.mitigation}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}
      </div>

      {showButtons && (
        <div className="flex gap-3 pt-2 border-t border-gray-100 shrink-0">
          <button
            onClick={onReject}
            className="flex-1 px-4 py-2.5 rounded-lg border border-red-200 text-red-600 text-sm font-medium hover:bg-red-50 transition-colors"
          >
            ✗ Reject
          </button>
          <button
            onClick={onApprove}
            className="flex-1 px-4 py-2.5 rounded-lg bg-green-600 text-white text-sm font-semibold hover:bg-green-700 transition-colors"
          >
            ✓ Approve — Start Engineering
          </button>
        </div>
      )}
    </div>
  );
}
