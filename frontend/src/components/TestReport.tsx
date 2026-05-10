import type { TestReport as TestReportType } from "../types";

interface Props {
  report: TestReportType;
}

const STATUS_CONFIG = {
  "pass":       { label: "All Tests Passed", classes: "bg-green-50 border-green-200 text-green-800", icon: "✓" },
  "fail-minor": { label: "Minor Failures",   classes: "bg-amber-50 border-amber-200 text-amber-800", icon: "⚠" },
  "fail-major": { label: "Major Failures",   classes: "bg-red-50 border-red-200 text-red-800",       icon: "✗" },
};

const SEVERITY_CLASSES = {
  minor:    "bg-amber-100 text-amber-700",
  major:    "bg-red-100 text-red-700",
  critical: "bg-red-200 text-red-900 font-semibold",
};

export function TestReport({ report }: Props) {
  const cfg = STATUS_CONFIG[report.status] ?? STATUS_CONFIG["fail-major"];

  return (
    <div className="space-y-4">
      {/* Status banner */}
      <div className={`rounded-lg border px-4 py-3 flex items-center gap-3 ${cfg.classes}`}>
        <span className="text-2xl">{cfg.icon}</span>
        <div>
          <p className="font-semibold text-sm">{cfg.label}</p>
          {report.summary && (
            <p className="text-xs mt-0.5 opacity-80">{report.summary}</p>
          )}
        </div>
      </div>

      {/* Passed */}
      {report.passed.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1.5">
            Passed ({report.passed.length})
          </h3>
          <ul className="space-y-0.5">
            {report.passed.map((t, i) => (
              <li key={i} className="flex items-center gap-2 text-sm font-mono text-green-700">
                <span>✓</span> {t}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Failed */}
      {report.failed.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1.5">
            Failed ({report.failed.length})
          </h3>
          <ul className="space-y-0.5">
            {report.failed.map((t, i) => (
              <li key={i} className="flex items-center gap-2 text-sm font-mono text-red-700">
                <span>✗</span> {t}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Defects */}
      {report.defects.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
            Defects ({report.defects.length})
          </h3>
          <div className="space-y-2">
            {report.defects.map((d) => (
              <div key={d.id} className="rounded-lg border border-gray-200 bg-white p-3 text-sm">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs px-1.5 py-0.5 rounded font-mono ${SEVERITY_CLASSES[d.severity] ?? "bg-gray-100 text-gray-700"}`}>
                    {d.severity}
                  </span>
                  <span className="font-mono text-gray-500 text-xs">
                    {d.file}{d.line ? `:${d.line}` : ""}
                  </span>
                  <span className="text-gray-400 text-xs ml-auto">{d.id}</span>
                </div>
                <p className="text-gray-700">{d.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
