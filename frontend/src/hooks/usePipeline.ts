import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../api/client";
import { useSSE } from "./useSSE";
import type { JobStatusResponse, PipelineStatus, SSEEvent } from "../types";

const POLL_INTERVAL_MS = 2500;
const TERMINAL_STATUSES: PipelineStatus[] = ["done", "failed", "waiting_approval", "waiting_clarification"];
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
  resume: (jobId: string) => void;
  rerunFromCheckpoint: () => Promise<void>;
  approve: () => Promise<void>;
  reject: () => Promise<void>;
  clarify: (text: string) => Promise<void>;
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

  const sseUrl = state.jobId && state.status === "running"
    ? api.streamUrl(state.jobId)
    : null;

  useSSE(sseUrl, {
    onEvent: useCallback((e: SSEEvent) => {
      setState((prev) => ({ ...prev, sseEvents: [...prev.sseEvents, e] }));
    }, []),
    onError: useCallback(() => {}, []),
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
        setState((prev) => ({ ...prev, status: data.status, jobData: data, error: null }));
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
    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
  }, [stopPolling]);

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
    try { await api.rejectSpec(state.jobId); } catch { }
    stopPolling();
    setState((prev) => ({ ...prev, status: "failed", error: "Spec rejected — pipeline cancelled." }));
  }, [state.jobId, stopPolling]);

  const clarify = useCallback(async (text: string) => {
    if (!state.jobId) return;
    try {
      await api.clarify(state.jobId, text);
      setState((prev) => ({ ...prev, status: "running", error: null, sseEvents: [] }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: `Clarification failed: ${err instanceof Error ? err.message : String(err)}`,
      }));
    }
  }, [state.jobId]);

  const cancel = useCallback(async () => {
    if (!state.jobId) return;
    stopPolling();
    try { await api.cancelJob(state.jobId); } catch { }
    setState((prev) => ({ ...prev, status: "failed", error: "Pipeline cancelled." }));
  }, [state.jobId, stopPolling]);

  const rerunFromCheckpoint = useCallback(async () => {
    if (!state.jobId) return;
    try {
      await api.resumeFromCheckpoint(state.jobId);
      setState((prev) => ({ ...prev, status: "running", error: null, sseEvents: [] }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: `Resume failed: ${err instanceof Error ? err.message : String(err)}`,
      }));
    }
  }, [state.jobId]);

  // Auto-discover MCP-started jobs when idle
  useEffect(() => {
    if (state.status !== "idle") return;
    const check = async () => {
      try {
        const { jobs } = await api.listJobs();
        const active =
          jobs.find((j) => j.status === "waiting_clarification") ??
          jobs.find((j) => j.status === "waiting_approval") ??
          jobs.find((j) => j.status === "running");
        if (active) {
          setState({ ...INITIAL, jobId: active.job_id, status: "running" });
        }
      } catch { }
    };
    check();
    const id = setInterval(check, DISCOVER_INTERVAL_MS);
    return () => clearInterval(id);
  }, [state.status]);

  const resume = useCallback((jobId: string) => {
    stopPolling();
    setState({ ...INITIAL, jobId, status: "running" });
  }, [stopPolling]);

  const reset = useCallback(() => {
    stopPolling();
    setState(INITIAL);
  }, [stopPolling]);

  return { ...state, start, resume, rerunFromCheckpoint, approve, reject, clarify, cancel, reset };
}
