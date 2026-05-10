import { useEffect, useRef, useCallback } from "react";
import type { SSEEvent } from "../types";

interface UseSSEOptions {
  onEvent: (e: SSEEvent) => void;
  onError?: (err: Event) => void;
}

/**
 * Opens an EventSource to `url` and calls `onEvent` for each message.
 * Closes automatically when `url` becomes null or component unmounts.
 */
export function useSSE(url: string | null, { onEvent, onError }: UseSSEOptions) {
  const esRef = useRef<EventSource | null>(null);
  const onEventRef = useRef(onEvent);
  const onErrorRef = useRef(onError);

  // Keep refs current without re-subscribing
  useEffect(() => { onEventRef.current = onEvent; }, [onEvent]);
  useEffect(() => { onErrorRef.current = onError; }, [onError]);

  const close = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
  }, []);

  useEffect(() => {
    if (!url) {
      close();
      return;
    }

    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (raw) => {
      try {
        const parsed = JSON.parse(raw.data) as SSEEvent;
        if (parsed.event === "stream_end") {
          close();
          return;
        }
        onEventRef.current(parsed);
      } catch {
        // ignore parse errors on malformed frames
      }
    };

    es.onerror = (err) => {
      onErrorRef.current?.(err);
      close();
    };

    return close;
  }, [url, close]);
}
