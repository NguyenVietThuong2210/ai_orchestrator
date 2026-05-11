import type { JobStatusResponse, JobListResponse, RunPipelineResponse } from "../types";

const BASE = "";  // relative — works for both Vite proxy and FastAPI static serve

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

  getStatus(jobId: string): Promise<JobStatusResponse> {
    return get(`/status/${jobId}`);
  },

  cancelJob(jobId: string): Promise<void> {
    return post(`/cancel/${jobId}`, {});
  },

  listJobs(): Promise<JobListResponse> {
    return get("/jobs");
  },

  streamUrl(jobId: string): string {
    return `${BASE}/stream/${jobId}`;
  },
};
