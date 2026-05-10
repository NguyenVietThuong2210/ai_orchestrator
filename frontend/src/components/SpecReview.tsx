import type { TechnicalSpec } from "../types";

interface Props {
  spec: TechnicalSpec;
  onApprove: () => void;
  onReject: () => void;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">{title}</h3>
      {children}
    </div>
  );
}

export function SpecReview({ spec, onApprove, onReject }: Props) {
  return (
    <div className="h-full flex flex-col gap-4">
      {/* Banner */}
      <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 flex items-start gap-3">
        <span className="text-amber-500 text-xl">⏸</span>
        <div>
          <p className="text-sm font-semibold text-amber-800">Human Gate — Spec Ready for Review</p>
          <p className="text-xs text-amber-700 mt-0.5">
            Review the technical spec below. Approve to start Engineering, or Reject to cancel.
          </p>
        </div>
      </div>

      {/* Spec content */}
      <div className="flex-1 overflow-y-auto space-y-5 scrollbar-thin pr-1">

        <Section title="Overview">
          <p className="text-sm text-gray-700 leading-relaxed">{spec.overview}</p>
        </Section>

        {spec.components.length > 0 && (
          <Section title="Components">
            <ul className="space-y-1">
              {spec.components.map((c, i) => (
                <li key={i} className="flex gap-2 text-sm">
                  <span className="font-mono text-blue-700 bg-blue-50 px-1.5 rounded text-xs self-start mt-0.5 whitespace-nowrap">
                    {c.name}
                  </span>
                  <span className="text-gray-600">{c.description}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {spec.api_contracts.length > 0 && (
          <Section title="API Contracts">
            <div className="space-y-1">
              {spec.api_contracts.map((c, i) => (
                <div key={i} className="flex items-center gap-2 text-sm font-mono">
                  <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                    {c.method}
                  </span>
                  <span className="text-gray-800">{c.path}</span>
                  {c.response && (
                    <span className="text-gray-400">→ {c.response}</span>
                  )}
                </div>
              ))}
            </div>
          </Section>
        )}

        {spec.data_models.length > 0 && (
          <Section title="Data Models">
            <ul className="space-y-1">
              {spec.data_models.map((m, i) => (
                <li key={i} className="text-sm">
                  <span className="font-mono font-medium text-gray-800">{m.name}</span>
                  {m.fields && m.fields.length > 0 && (
                    <span className="text-gray-500 ml-2">
                      — {m.fields
                          .map((f) => (typeof f === "string" ? f : (f as Record<string,unknown>).name ?? JSON.stringify(f)))
                          .join(", ")}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {spec.risks.length > 0 && (
          <Section title="Risks">
            <ul className="space-y-1">
              {spec.risks.map((r, i) => (
                <li key={i} className="flex gap-2 text-sm">
                  <span className="text-amber-500">⚠</span>
                  <span className="text-gray-600">{r.description}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {spec.acceptance_criteria.length > 0 && (
          <Section title="Acceptance Criteria">
            <ul className="space-y-1">
              {spec.acceptance_criteria.map((c, i) => (
                <li key={i} className="flex gap-2 text-sm">
                  <span className="text-gray-400 mt-0.5">□</span>
                  <span className="text-gray-700">{c}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 pt-2 border-t border-gray-100">
        <button
          onClick={onReject}
          className="flex-1 px-4 py-2.5 rounded-lg border border-red-200 text-red-600 text-sm font-medium hover:bg-red-50 transition-colors"
        >
          Reject &amp; Cancel
        </button>
        <button
          onClick={onApprove}
          className="flex-1 px-4 py-2.5 rounded-lg bg-green-600 text-white text-sm font-semibold hover:bg-green-700 transition-colors"
        >
          Approve — Start Engineering ▶
        </button>
      </div>
    </div>
  );
}
