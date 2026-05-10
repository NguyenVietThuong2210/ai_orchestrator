import { useState } from "react";
import type { PipelineStatus } from "../types";

interface Props {
  status: PipelineStatus;
  onStart: (requirement: string) => void;
  onCancel: () => void;
  onReset: () => void;
  cancelPending?: boolean;
}

const PLACEHOLDER = `Describe what you want to build…

Example:
Build a minimal Django "Hello World" web app.
Store all files under projects/hello_django/.
The app must have one view at / that returns "Hello, World!"
and must be runnable with: python manage.py runserver`;

export function PipelineForm({ status, onStart, onCancel, onReset, cancelPending = false }: Props) {
  const [requirement, setRequirement] = useState("");

  const isActive = status === "running" || status === "starting" || status === "waiting_approval";
  const isTerminal = status === "done" || status === "failed";

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (requirement.trim().length < 10) return;
    onStart(requirement.trim());
  }

  if (isTerminal) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-gray-500">Pipeline finished.</p>
        <button
          onClick={onReset}
          className="w-full px-4 py-2 rounded-lg bg-gray-900 text-white text-sm font-medium hover:bg-gray-700 transition-colors"
        >
          New Pipeline
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <textarea
        value={requirement}
        onChange={(e) => setRequirement(e.target.value)}
        placeholder={PLACEHOLDER}
        disabled={isActive}
        rows={10}
        className="w-full text-sm rounded-lg border border-gray-200 bg-white p-3 resize-none
                   placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500
                   disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed
                   font-mono leading-relaxed"
      />
      <div className="flex gap-2">
        {isActive ? (
          <button
            type="button"
            onClick={onCancel}
            disabled={cancelPending}
            className="flex-1 px-4 py-2 rounded-lg border border-red-200 text-red-600 text-sm font-medium hover:bg-red-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {cancelPending ? "Cancelling…" : "Cancel"}
          </button>
        ) : (
          <button
            type="submit"
            disabled={requirement.trim().length < 10}
            className="flex-1 px-4 py-2 rounded-lg bg-gray-900 text-white text-sm font-medium
                       hover:bg-gray-700 transition-colors
                       disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Run Pipeline ▶
          </button>
        )}
      </div>
    </form>
  );
}
