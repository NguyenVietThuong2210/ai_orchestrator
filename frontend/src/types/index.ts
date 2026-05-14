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

export interface Component {
  name: string;
  responsibility: string;
  dependencies?: string[];
}

export interface ApiContract {
  method: string;
  path: string;
  request_schema?: Record<string, unknown>;
  response_schema?: Record<string, unknown>;
  errors?: string[];
  // legacy fields from older runs
  response?: string;
  description?: string;
}

export interface DataModel {
  name: string;
  fields: Array<string | Record<string, unknown>>;
  description?: string;
}

export interface Risk {
  description: string;
  severity?: "low" | "medium" | "high";
  mitigation?: string;
  // legacy
  id?: string;
}

export interface TechnicalSpec {
  overview: string;
  components: Component[];
  api_contracts: ApiContract[];
  data_models: DataModel[];
  risks: Risk[];
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

export interface JobSummary {
  job_id: string;
  status: string;
}

export interface JobListResponse {
  jobs: JobSummary[];
}

// UI-layer SSE event (parsed from EventSource)
export interface SSEEvent {
  event: string;
  name: string;
  data: string;
}
