import { useEffect, useRef, useCallback } from "react";
import type { SSEEvent } from "../types";

interface UseSSEOptions {
  onEvent: (e: SSEEvent) => void;
  onError?: (err: Event) => void;
}

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 1000;

/**
 * Opens an EventSource to `url` and calls `onEvent` for each message.
 * Closes automatically when `url` becomes null or component unmounts.
 * Reconnects up to MAX_RETRIES times with exponential backoff on error.
 */
export function useSSE(url: string | null, { onEvent, onError }: UseSSEOptions) {
  const esRef    = useRef<EventSource | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retries  = useRef(0);

  const onEventRef = useRef(onEvent);
  const onErrorRef = useRef(onError);

  useEffect(() => { onEventRef.current = onEvent; }, [onEvent]);
  useEffect(() => { onErrorRef.current = onError; }, [onError]);

  const close = useCallback(() => {
    if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
    esRef.current?.close();
    esRef.current = null;
  }, []);

  const connect = useCallback((targetUrl: string) => {
    close();

    const es = new EventSource(targetUrl);
    esRef.current = es;

    es.onmessage = (raw) => {
      retries.current = 0; // reset on successful message
      try {
        const parsed = JSON.parse(raw.data) as SSEEvent;
        if (parsed.event === "stream_end") {
          close();
          return;
        }
        onEventRef.current(parsed);
      } catch {
        // ignore malformed frames
      }
    };

    es.onerror = (err) => {
      onErrorRef.current?.(err);
      es.close();
      esRef.current = null;

      if (retries.current < MAX_RETRIES) {
        const delay = BASE_DELAY_MS * 2 ** retries.current;
        retries.current += 1;
        timerRef.current = setTimeout(() => connect(targetUrl), delay);
      }
    };
  }, [close]);

  useEffect(() => {
    if (!url) {
      retries.current = 0;
      close();
      return close;
    }

    retries.current = 0;
    connect(url);
    return close;
  }, [url, connect, close]);
}
