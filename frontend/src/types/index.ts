// Mirrors backend Pydantic schemas and ProjectContext TypedDict

export type PipelineStatus =
  | "idle"
  | "starting"
  | "running"
  | "waiting_approval"
  | "done"
  | "failed";

export interface AgentEvent {
  agent: string;
  timestamp: string;
  status: string;
  tokens_used: number;
  duration_seconds: number;
  note: string;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  priority: number;
  status: string;
}

export interface TechnicalSpec {
  overview: string;
  components: Array<{ name: string; description: string }>;
  api_contracts: Array<{ method: string; path: string; response: string }>;
  data_models: Array<{ name: string; fields: string[] }>;
  risks: Array<{ id: string; description: string }>;
  acceptance_criteria: string[];
}

export interface Defect {
  id: string;
  severity: "minor" | "major" | "critical";
  description: string;
  file: string;
  line: number;
}

export interface TestReport {
  status: "pass" | "fail-minor" | "fail-major";
  summary: string;
  passed: string[];
  failed: string[];
  defects: Defect[];
}

export interface JobStatusResponse {
  job_id: string;
  status: PipelineStatus;
  current_node: string;
  iteration: number;
  qa_analyser_iteration: number;
  artifact_paths: Record<string, string>;
  tasks: Task[];
  spec: TechnicalSpec | null;
  test_report: TestReport | null;
  history: AgentEvent[];
  cost_estimate_usd: number | null;
  project_dir: string | null;
  spec_dir: string | null;
}

export interface RunPipelineResponse {
  job_id: string;
  status: string;
  message: string;
}

// UI-layer SSE event (parsed from EventSource)
export interface SSEEvent {
  event: string;
  name: string;
  data: string;
}
