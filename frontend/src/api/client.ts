import type {
  JobStatusResponse,
  JobListResponse,
  RunPipelineResponse,
  InjectMessageResponse,
  ModifySpecResponse,
  ProjectListResponse,
  RunListResponse,
} from "../types";

const BASE = "";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  runPipeline(requirement: string, jobId?: string): Promise<RunPipelineResponse> {
    return post("/run-pipeline", { requirement, job_id: jobId ?? null });
  },

  approveSpec(jobId: string): Promise<void> {
    return post("/approve-spec", { job_id: jobId, decision: "approve" });
  },

  rejectSpec(jobId: string): Promise<void> {
    return post("/approve-spec", { job_id: jobId, decision: "reject" });
  },

  clarify(jobId: string, clarificationContext: string): Promise<void> {
    return post(`/clarify/${jobId}`, { job_id: jobId, clarification_context: clarificationContext });
  },

  injectMessage(jobId: string, message: string, targetAgent = "any"): Promise<InjectMessageResponse> {
    return post(`/inject/${jobId}`, { message, target_agent: targetAgent });
  },

  modifySpec(jobId: string, specMd?: string, planMd?: string, note?: string): Promise<ModifySpecResponse> {
    return post(`/modify-spec/${jobId}`, {
      spec_md: specMd ?? null,
      plan_md: planMd ?? null,
      note: note ?? "",
    });
  },

  pauseJob(jobId: string, reason?: string): Promise<{ job_id: string; status: string; message: string }> {
    return post(`/pause/${jobId}`, { reason: reason ?? "" });
  },

  getStatus(jobId: string): Promise<JobStatusResponse> {
    return get(`/status/${jobId}`);
  },

  cancelJob(jobId: string): Promise<void> {
    return post(`/cancel/${jobId}`, {});
  },

  resumeFromCheckpoint(jobId: string): Promise<{ job_id: string; status: string; message: string }> {
    return post(`/resume/${jobId}`, {});
  },

  listJobs(): Promise<JobListResponse> {
    return get("/jobs");
  },

  artifactUrl(jobId: string, filename: string): string {
    return `${BASE}/artifact/${jobId}/${encodeURIComponent(filename)}`;
  },

  streamUrl(jobId: string): string {
    return `${BASE}/stream/${jobId}`;
  },

  listProjects(): Promise<ProjectListResponse> {
    return get("/projects");
  },

  listProjectRuns(projectName: string): Promise<RunListResponse> {
    return get(`/projects/${encodeURIComponent(projectName)}/runs`);
  },

  getRunSnapshot(projectName: string, jobId: string): Promise<JobStatusResponse> {
    return get(`/projects/${encodeURIComponent(projectName)}/runs/${jobId}`);
  },

  solutionUrl(): string {
    return `${BASE}/solution`;
  },
};
