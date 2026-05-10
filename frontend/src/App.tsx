import { usePipeline } from "./hooks/usePipeline";
import { StatusBadge } from "./components/StatusBadge";
import { PipelineForm } from "./components/PipelineForm";
import { AgentTimeline } from "./components/AgentTimeline";
import { SpecReview } from "./components/SpecReview";
import { ArtifactList } from "./components/ArtifactList";
import { TestReport } from "./components/TestReport";

function MainPanel({
  pipeline,
}: {
  pipeline: ReturnType<typeof usePipeline>;
}) {
  const { status, jobData, sseEvents, error, approve, reject } = pipeline;

  if (status === "idle") {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center gap-4 text-gray-400">
        <div className="text-6xl">🤖</div>
        <div>
          <p className="text-lg font-medium text-gray-600">AI Orchestrator</p>
          <p className="text-sm mt-1">Describe what you want to build in the sidebar, then click Run.</p>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 text-left max-w-md w-full">
          {[
            { agent: "PM", desc: "Breaks requirements into tasks" },
            { agent: "Analyser", desc: "Writes technical spec" },
            { agent: "Engineer", desc: "Implements the code" },
            { agent: "QA", desc: "Validates and tests output" },
          ].map(({ agent, desc }) => (
            <div key={agent} className="rounded-lg border border-gray-100 bg-white p-3">
              <p className="text-xs font-semibold text-gray-700">{agent}</p>
              <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (status === "starting") {
    return (
      <div className="flex items-center justify-center h-full gap-3 text-gray-500">
        <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm">Starting pipeline…</span>
      </div>
    );
  }

  if (status === "running") {
    return (
      <div className="h-full p-6">
        <AgentTimeline
          history={jobData?.history ?? []}
          sseEvents={sseEvents}
          iteration={jobData?.iteration ?? 0}
          qaAnalyserIteration={jobData?.qa_analyser_iteration ?? 0}
        />
      </div>
    );
  }

  if (status === "waiting_approval" && jobData?.spec) {
    return (
      <div className="h-full p-6">
        <SpecReview
          spec={jobData.spec}
          onApprove={approve}
          onReject={reject}
        />
      </div>
    );
  }

  if (status === "done" && jobData) {
    return (
      <div className="h-full overflow-y-auto p-6 space-y-6 scrollbar-thin">
        <div className="rounded-xl bg-green-50 border border-green-200 px-5 py-4 flex items-center gap-3">
          <span className="text-3xl">✅</span>
          <div>
            <p className="font-semibold text-green-800">Pipeline Complete</p>
            <p className="text-xs text-green-700 mt-0.5">
              Job <span className="font-mono">{jobData.job_id}</span> finished successfully.
              {jobData.cost_estimate_usd === 0 && " Cost: $0 (Mode B)"}
            </p>
          </div>
        </div>

        {jobData.test_report && (
          <section>
            <h2 className="text-sm font-semibold text-gray-700 mb-3">QA Report</h2>
            <TestReport report={jobData.test_report} />
          </section>
        )}

        {Object.keys(jobData.artifact_paths).length > 0 && (
          <section>
            <ArtifactList artifactPaths={jobData.artifact_paths} />
          </section>
        )}

        {jobData.history.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Agent History</h2>
            <AgentTimeline
              history={jobData.history}
              sseEvents={[]}
              iteration={jobData.iteration}
              qaAnalyserIteration={jobData.qa_analyser_iteration}
            />
          </section>
        )}
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="h-full overflow-y-auto p-6 space-y-4 scrollbar-thin">
        <div className="rounded-xl bg-red-50 border border-red-200 px-5 py-4 flex items-start gap-3">
          <span className="text-3xl">❌</span>
          <div>
            <p className="font-semibold text-red-800">Pipeline Failed</p>
            {error && (
              <p className="text-xs text-red-700 font-mono mt-1 whitespace-pre-wrap">{error}</p>
            )}
          </div>
        </div>

        {jobData?.test_report && (
          <section>
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Last QA Report</h2>
            <TestReport report={jobData.test_report} />
          </section>
        )}

        {jobData?.history && jobData.history.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Agent History</h2>
            <AgentTimeline
              history={jobData.history}
              sseEvents={[]}
              iteration={jobData.iteration}
              qaAnalyserIteration={jobData.qa_analyser_iteration}
            />
          </section>
        )}
      </div>
    );
  }

  return null;
}

export default function App() {
  const pipeline = usePipeline();

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 bg-gray-900 text-white border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xl">🤖</span>
          <span className="font-semibold tracking-tight">AI Orchestrator</span>
          {pipeline.jobId && (
            <span className="text-xs font-mono text-gray-400 ml-2">
              {pipeline.jobId}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <StatusBadge status={pipeline.status} />
          <a
            href="/docs"
            target="_blank"
            className="text-xs text-gray-400 hover:text-white transition-colors"
          >
            API Docs ↗
          </a>
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 min-h-0">
        {/* Sidebar */}
        <aside className="w-72 shrink-0 bg-white border-r border-gray-100 flex flex-col p-4 gap-4 overflow-y-auto">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">
              New Pipeline
            </p>
            <PipelineForm
              status={pipeline.status}
              onStart={pipeline.start}
              onCancel={pipeline.cancel}
              onReset={pipeline.reset}
            />
          </div>

          {/* Pipeline step indicators */}
          {pipeline.status !== "idle" && (
            <div className="mt-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                Steps
              </p>
              <StepIndicator
                status={pipeline.status}
                currentNode={pipeline.jobData?.current_node ?? null}
              />
            </div>
          )}
        </aside>

        {/* Main panel */}
        <main className="flex-1 min-w-0 overflow-hidden">
          <MainPanel pipeline={pipeline} />
        </main>
      </div>
    </div>
  );
}

// Map LangGraph node names → step keys
const NODE_TO_STEP: Record<string, string> = {
  pm:         "pm",
  analyser:   "analyser",
  human_gate: "gate",
  engineer:   "engineer",
  qa:         "qa",
};

// A step is "done" once the pipeline has moved past it
const STEP_ORDER = ["pm", "analyser", "gate", "engineer", "qa"];

function StepIndicator({
  status,
  currentNode,
}: {
  status: string;
  currentNode: string | null;
}) {
  const steps = [
    { key: "pm",       label: "PM" },
    { key: "analyser", label: "Analyser" },
    { key: "gate",     label: "Review" },
    { key: "engineer", label: "Engineer" },
    { key: "qa",       label: "QA" },
  ];

  // Determine the active step from the real LangGraph node name
  const activeStep = (status === "starting")
    ? "pm"
    : (status === "waiting_approval")
      ? "gate"
      : (currentNode ? NODE_TO_STEP[currentNode] ?? null : null);

  const activeIdx = activeStep ? STEP_ORDER.indexOf(activeStep) : -1;
  const isTerminal = status === "done" || status === "failed";

  return (
    <ol className="space-y-1">
      {steps.map(({ key, label }, idx) => {
        const isDone = isTerminal
          ? status === "done"                   // all green on done, none on failed
          : activeIdx > idx;                    // steps before current are done
        const isCurrent = !isTerminal && activeStep === key;

        return (
          <li key={key} className="flex items-center gap-2 text-xs">
            <span className={`w-4 h-4 rounded-full flex items-center justify-center text-xs shrink-0
              ${isDone     ? "bg-green-500 text-white" :
                isCurrent  ? "bg-blue-500 text-white animate-pulse" :
                             "bg-gray-200 text-gray-400"}`}>
              {isDone ? "✓" : "·"}
            </span>
            <span className={
              isDone    ? "text-gray-700" :
              isCurrent ? "text-blue-700 font-medium" :
                          "text-gray-400"
            }>
              {label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
