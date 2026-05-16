// Mirrors backend Pydantic schemas and ProjectContext TypedDict

export type PipelineStatus =
  | "idle"
  | "starting"
  | "running"
  | "waiting_clarification"
  | "waiting_approval"
  | "done"
  | "failed";

export type PipelineIntent = "query" | "test" | "bug_fix" | "feature" | "review";

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
  phase?: string;
  depends_on?: string[];
  parallel?: boolean;
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

export interface CodeReviewReport {
  status: "pass" | "fail";
  issues: Array<{ file: string; line: number; severity: string; description: string }>;
  summary: string;
}

export interface SecurityReport {
  status: "pass" | "warn" | "fail";
  vulnerabilities: Array<{ tool: string; id: string; severity: string; description: string; file: string }>;
  summary: string;
}

export interface DeployReport {
  status: "pass" | "fail";
  endpoint: string;
  response: string;
  command_used: string;
}

export interface Retrospective {
  what_worked: string[];
  what_failed: string[];
  lessons: string[];
  metrics: Record<string, unknown>;
}

export interface SpecAnalysisFinding {
  pass_name: "duplication" | "ambiguity" | "underspecification" | "constitution" | "coverage";
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  location: string;
  description: string;
  suggestion: string;
}

export interface SpecAnalysisReport {
  findings: SpecAnalysisFinding[];
  summary: string;
  approved: boolean;
}

export interface UserMessage {
  from_user: string;
  target_agent: string;
  timestamp: string;
  job_id: string;
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
  error?: string | null;
  // PM clarification
  definition_of_done: string[];
  needs_clarification: boolean;
  clarification_questions: string[];
  // Post-engineering reports
  code_review_report: CodeReviewReport | null;
  security_report: SecurityReport | null;
  deploy_report: DeployReport | null;
  retrospective: Retrospective | null;
  // Adaptive pipeline
  pipeline_intent: PipelineIntent;
  // SDD Speckit artifacts
  spec_md: string;
  plan_md: string;
  tasks_md: string;
  constitution: string;
  // Spec analysis
  spec_analysis: SpecAnalysisReport | null;
  spec_revision_count: number;
  // Multi-point interaction
  user_message_queue: UserMessage[];
  interaction_log: Record<string, unknown>[];
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

export interface RunSummary {
  job_id: string;
  project_name: string;
  pipeline_intent: string;
  status: string;
  created_at: string;
  request_snippet: string;
  task_count: number;
}

export interface ProjectSummary {
  project_name: string;
  latest_run: string;
  run_count: number;
  last_updated: string;
  status: string;
}

export interface ProjectListResponse {
  projects: ProjectSummary[];
}

export interface RunListResponse {
  project_name: string;
  runs: RunSummary[];
}

export interface InjectMessageResponse {
  job_id: string;
  status: string;
  message: string;
  queue_length: number;
}

export interface ModifySpecResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface SSEEvent {
  event: string;
  name: string;
  data: string;
}
