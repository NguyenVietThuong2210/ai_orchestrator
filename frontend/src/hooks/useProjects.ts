import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import type { ProjectSummary, RunSummary } from "../types";

export interface UseProjectsReturn {
  projects: ProjectSummary[];
  loading: boolean;
  expandedProject: string | null;
  projectRuns: Record<string, RunSummary[]>;
  runsLoading: Record<string, boolean>;
  toggleProject: (name: string) => void;
  refresh: () => void;
}

export function useProjects(pollIntervalMs = 30000): UseProjectsReturn {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedProject, setExpandedProject] = useState<string | null>(null);
  const [projectRuns, setProjectRuns] = useState<Record<string, RunSummary[]>>({});
  const [runsLoading, setRunsLoading] = useState<Record<string, boolean>>({});

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.listProjects();
      setProjects(res.projects);
    } catch {
      // silently ignore — DB may not be available
    } finally {
      setLoading(false);
    }
  }, []);

  const toggleProject = useCallback(async (name: string) => {
    if (expandedProject === name) {
      setExpandedProject(null);
      return;
    }
    setExpandedProject(name);
    if (projectRuns[name]) return; // already loaded

    setRunsLoading((prev) => ({ ...prev, [name]: true }));
    try {
      const res = await api.listProjectRuns(name);
      setProjectRuns((prev) => ({ ...prev, [name]: res.runs }));
    } catch {
      setProjectRuns((prev) => ({ ...prev, [name]: [] }));
    } finally {
      setRunsLoading((prev) => ({ ...prev, [name]: false }));
    }
  }, [expandedProject, projectRuns]);

  useEffect(() => {
    fetchProjects();
    const id = setInterval(fetchProjects, pollIntervalMs);
    return () => clearInterval(id);
  }, [fetchProjects, pollIntervalMs]);

  return { projects, loading, expandedProject, projectRuns, runsLoading, toggleProject, refresh: fetchProjects };
}
