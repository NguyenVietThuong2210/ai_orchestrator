import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../api/client";
import { useSSE } from "./useSSE";
import type { JobStatusResponse, PipelineStatus, SSEEvent } from "../types";

const POLL_INTERVAL_MS = 2500;
const TERMINAL_STATUSES: PipelineStatus[] = ["done", "failed", "waiting_approval"];

export interface PipelineState {
  jobId: string | null;
  status: PipelineStatus;
  jobData: JobStatusResponse | null;
  sseEvents: SSEEvent[];
  error: string | null;
}

export interface PipelineActions {
  start: (requirement: string) => Promise<void>;
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

  // SSE — active only when running
  const sseUrl = state.jobId && state.status === "running"
    ? api.streamUrl(state.jobId)
    : null;

  useSSE(sseUrl, {
    onEvent: useCallback((e: SSEEvent) => {
      setState((prev) => ({ ...prev, sseEvents: [...prev.sseEvents, e] }));
    }, []),
  });

  // Polling — stops at terminal states
  const poll = useCallback(async (jobId: string) => {
    try {
      const data = await api.getStatus(jobId);
      setState((prev) => ({
        ...prev,
        status: data.status,
        jobData: data,
        error: null,
      }));
      if (TERMINAL_STATUSES.includes(data.status)) {
        if (pollRef.current) clearInterval(pollRef.current);
      }
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : String(err),
      }));
    }
  }, []);

  useEffect(() => {
    if (!state.jobId || state.status === "idle" || state.status === "starting") return;
    if (TERMINAL_STATUSES.includes(state.status) && state.status !== "running") return;

    pollRef.current = setInterval(() => poll(state.jobId!), POLL_INTERVAL_MS);
    poll(state.jobId);   // immediate first fetch

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [state.jobId, poll]);   // intentionally exclude state.status — re-subscribing on status change causes double-intervals

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
    await api.approveSpec(state.jobId);
    setState((prev) => ({ ...prev, status: "running" }));
    // Clear any stale interval ref before creating a new one
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(() => poll(state.jobId!), POLL_INTERVAL_MS);
    poll(state.jobId);   // immediate fetch so UI updates without waiting one full interval
  }, [state.jobId, poll]);

  const reject = useCallback(async () => {
    if (!state.jobId) return;
    await api.rejectSpec(state.jobId);
    setState((prev) => ({ ...prev, status: "failed" }));
  }, [state.jobId]);

  const cancel = useCallback(async () => {
    if (!state.jobId) return;
    await api.cancelJob(state.jobId);
    setState((prev) => ({ ...prev, status: "failed" }));
    if (pollRef.current) clearInterval(pollRef.current);
  }, [state.jobId]);

  const reset = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    setState(INITIAL);
  }, []);

  return { ...state, start, approve, reject, cancel, reset };
}
