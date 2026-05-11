import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../api/client";
import { useSSE } from "./useSSE";
import type { JobStatusResponse, PipelineStatus, SSEEvent } from "../types";

const POLL_INTERVAL_MS = 2500;
const TERMINAL_STATUSES: PipelineStatus[] = ["done", "failed", "waiting_approval"];
// How often to check /jobs for MCP-started pipelines when the UI is idle
const DISCOVER_INTERVAL_MS = 3000;

export interface PipelineState {
  jobId: string | null;
  status: PipelineStatus;
  jobData: JobStatusResponse | null;
  sseEvents: SSEEvent[];
  error: string | null;
}

export interface PipelineActions {
  start: (requirement: string) => Promise<void>;
  resume: (jobId: string) => void;  // load an existing job by ID into local state
  approve: () => Promise<void>;
  reject: () => Promise<void>;
  cancel: () => Promise<void>;
  reset: () => void;
}

const INITIAL: PipelineState = {
  jobId: null,
  status: "idle",
  jobData: null,
  sseEvents: [],
  error: null,
};

export function usePipeline(): PipelineState & PipelineActions {
  const [state, setState] = useState<PipelineState>(INITIAL);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // SSE — active only while running (not during approval wait or terminal states)
  const sseUrl = state.jobId && state.status === "running"
    ? api.streamUrl(state.jobId)
    : null;

  useSSE(sseUrl, {
    onEvent: useCallback((e: SSEEvent) => {
      setState((prev) => ({ ...prev, sseEvents: [...prev.sseEvents, e] }));
    }, []),
    onError: useCallback(() => {
      // SSE errors are surfaced via the reconnect logic in useSSE; no state change here
    }, []),
  });

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback((jobId: string) => {
    stopPolling();
    const poll = async () => {
      try {
        const data = await api.getStatus(jobId);
        setState((prev) => ({
          ...prev,
          status: data.status,
          jobData: data,
          error: null,
        }));
        if (TERMINAL_STATUSES.includes(data.status)) {
          stopPolling();
        }
      } catch (err) {
        setState((prev) => ({
          ...prev,
          error: err instanceof Error ? err.message : String(err),
        }));
      }
    };
    poll(); // immediate first fetch
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
  }, [stopPolling]);

  // Start polling when we have a jobId and are in running state
  useEffect(() => {
    if (!state.jobId || state.status !== "running") return;
    startPolling(state.jobId);
    return stopPolling;
  }, [state.jobId, state.status, startPolling, stopPolling]);

  const start = useCallback(async (requirement: string) => {
    setState({ ...INITIAL, status: "starting" });
    try {
      const res = await api.runPipeline(requirement);
      setState((prev) => ({ ...prev, jobId: res.job_id, status: "running" }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        status: "failed",
        error: err instanceof Error ? err.message : String(err),
      }));
    }
  }, []);

  const approve = useCallback(async () => {
    if (!state.jobId) return;
    try {
      await api.approveSpec(state.jobId);
      // Transition to running — triggers useEffect above to restart polling
      setState((prev) => ({ ...prev, status: "running", error: null, sseEvents: [] }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: `Approval failed: ${err instanceof Error ? err.message : String(err)}`,
      }));
    }
  }, [state.jobId]);

  const reject = useCallback(async () => {
    if (!state.jobId) return;
    try {
      await api.rejectSpec(state.jobId);
    } catch {
      // Rejection API may error (e.g. 404 if job already gone) — still mark failed locally
    }
    stopPolling();
    setState((prev) => ({
      ...prev,
      status: "failed",
      error: "Spec rejected — pipeline cancelled.",
    }));
  }, [state.jobId, stopPolling]);

  const cancel = useCallback(async () => {
    if (!state.jobId) return;
    stopPolling();
    try {
      await api.cancelJob(state.jobId);
    } catch {
      // Cancel may fail if job already finished — treat as success locally
    }
    setState((prev) => ({ ...prev, status: "failed", error: "Pipeline cancelled." }));
  }, [state.jobId, stopPolling]);

  // Auto-discover MCP-started jobs: poll /jobs when idle, load the most recent active one.
  // Prefers waiting_approval (human gate) over running, to surface the job needing action.
  useEffect(() => {
    if (state.status !== "idle") return;
    const check = async () => {
      try {
        const { jobs } = await api.listJobs();
        // Prefer waiting_approval first (needs human action), then running
        const active =
          jobs.find((j) => j.status === "waiting_approval") ??
          jobs.find((j) => j.status === "running");
        if (active) {
          setState({ ...INITIAL, jobId: active.job_id, status: "running" });
        }
      } catch {
        // server may not be ready yet — silently ignore
      }
    };
    check(); // immediate check on mount / when reset to idle
    const id = setInterval(check, DISCOVER_INTERVAL_MS);
    return () => clearInterval(id);
  }, [state.status]);

  const resume = useCallback((jobId: string) => {
    stopPolling();
    // Seed local state with the given jobId and "running" so the polling useEffect
    // fires immediately. The first poll will correct the status to the real value
    // (e.g. "waiting_approval") returned by the API.
    setState({ ...INITIAL, jobId, status: "running" });
  }, [stopPolling]);

  const reset = useCallback(() => {
    stopPolling();
    setState(INITIAL);
  }, [stopPolling]);

  return { ...state, start, resume, approve, reject, cancel, reset };
}
