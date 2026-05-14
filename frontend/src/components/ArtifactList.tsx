interface Props {
  artifactPaths: Record<string, string>;
  specDir?: string | null;
  projectDir?: string | null;
}

const SPEC_FILES = [
  { file: "00_requirements.md",      label: "Requirements",       icon: "📄" },
  { file: "01_pm_tasks.md",          label: "PM Tasks",           icon: "📋" },
  { file: "01_pm_tasks.json",        label: "PM Tasks (JSON)",    icon: "{ }" },
  { file: "02_technical_spec.md",    label: "Technical Spec",     icon: "🔍" },
  { file: "02_technical_spec.json",  label: "Spec (JSON)",        icon: "{ }" },
  { file: "03_engineer_summary.md",  label: "Engineer Summary",   icon: "⚙️"  },
  { file: "03_engineer_summary.json",label: "Engineer (JSON)",    icon: "{ }" },
  { file: "_pipeline.json",          label: "Pipeline Manifest",  icon: "🗂"  },
];

export function ArtifactList({ artifactPaths, specDir, projectDir }: Props) {
  const codeEntries = Object.entries(artifactPaths);

  return (
    <div className="space-y-5">

      {/* Project root */}
      {projectDir && (
        <div className="rounded-lg bg-gray-800 px-3 py-2 flex items-center gap-2">
          <span className="text-base shrink-0">📂</span>
          <div>
            <p className="text-[10px] text-gray-400 uppercase tracking-wide">Project Root</p>
            <p className="text-xs font-mono text-green-300 break-all">{projectDir}</p>
          </div>
        </div>
      )}

      {/* Spec folder */}
      {specDir && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-base">📁</span>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500">
              Spec Folder
            </h3>
            <span className="text-xs font-mono text-gray-400">{specDir}</span>
          </div>
          <div className="rounded-lg border border-blue-100 bg-blue-50 divide-y divide-blue-100 overflow-hidden">
            {SPEC_FILES.map(({ file, label, icon }) => (
              <div key={file} className="flex items-center gap-2 px-3 py-1.5 text-xs">
                <span className="text-base shrink-0">{icon}</span>
                <span className="font-mono text-blue-800 font-medium">{file}</span>
                <span className="text-blue-500 ml-auto">{label}</span>
              </div>
            ))}
            {/* QA retries — shown generically */}
            <div className="flex items-center gap-2 px-3 py-1.5 text-xs text-blue-400 italic">
              <span className="text-base shrink-0">📝</span>
              <span className="font-mono">04_qa_report[_rN].{"{json,md}"}</span>
              <span className="ml-auto">QA Reports (per retry)</span>
            </div>
          </div>
        </div>
      )}

      {/* Code artifacts */}
      {codeEntries.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-base">📦</span>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500">
              Generated Files ({codeEntries.length})
            </h3>
          </div>
          <div className="rounded-lg border border-gray-200 divide-y divide-gray-100 overflow-hidden">
            {codeEntries.map(([name, path]) => (
              <div key={name} className="flex items-center gap-2 px-3 py-1.5 text-xs">
                <span className="text-base shrink-0">📄</span>
                <span className="font-mono text-gray-800 font-medium min-w-0 truncate" title={name}>
                  {name}
                </span>
                <span className="font-mono text-gray-400 ml-auto shrink-0 truncate max-w-[40%]" title={path}>
                  {path}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {!specDir && !projectDir && codeEntries.length === 0 && (
        <div className="flex flex-col items-center justify-center pt-12 gap-3 text-gray-400">
          <span className="text-4xl">⚙️</span>
          <p className="text-sm">No code artifacts yet.</p>
          <p className="text-xs opacity-70">Files appear here after the Engineer agent completes.</p>
        </div>
      )}
    </div>
  );
}
