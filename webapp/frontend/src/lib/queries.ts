import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type {
  FactsPayload,
  GuardrailsPayload,
  ImportCandidate,
  Project,
  ProjectDetail,
  ProfilePayload,
  ResumePayload,
  Settings,
  SystemInfo,
  TrashItem,
  Version,
} from "./types";

export const keys = {
  system: ["system"] as const,
  settings: ["settings"] as const,
  projects: ["projects"] as const,
  project: (id: string) => ["project", id] as const,
  versions: (id: string) => ["project", id, "versions"] as const,
  report: (id: string) => ["project", id, "report"] as const,
  projectFacts: (id: string) => ["project", id, "facts"] as const,
  profile: ["profile"] as const,
  resume: ["resume"] as const,
  facts: ["facts"] as const,
  guardrails: ["guardrails"] as const,
  trash: ["trash"] as const,
  importCandidates: ["import-candidates"] as const,
};

export const useSystem = () =>
  useQuery({ queryKey: keys.system, queryFn: () => api.get<SystemInfo>("/api/system"), staleTime: 30_000 });

export const useSettings = () => useQuery({ queryKey: keys.settings, queryFn: () => api.get<Settings>("/api/settings") });

export const useProjects = () =>
  useQuery({ queryKey: keys.projects, queryFn: () => api.get<Project[]>("/api/projects") });

export const useProject = (id: string) =>
  useQuery({ queryKey: keys.project(id), queryFn: () => api.get<ProjectDetail>(`/api/projects/${id}`) });

export const useVersions = (id: string, enabled = true) =>
  useQuery({ queryKey: keys.versions(id), queryFn: () => api.get<Version[]>(`/api/projects/${id}/versions`), enabled });

export const useReport = (id: string, enabled = true) =>
  useQuery({ queryKey: keys.report(id), queryFn: () => api.get<string>(`/api/projects/${id}/report`), enabled, retry: false });

export const useProjectFacts = (id: string) =>
  useQuery({
    queryKey: keys.projectFacts(id),
    queryFn: () => api.get<Record<string, { text: string; employer: string; kind: string }>>(`/api/projects/${id}/facts`),
    staleTime: 60_000,
  });

export const useProfile = () => useQuery({ queryKey: keys.profile, queryFn: () => api.get<ProfilePayload>("/api/profile") });
export const useResume = () => useQuery({ queryKey: keys.resume, queryFn: () => api.get<ResumePayload>("/api/resume") });
export const useFacts = () => useQuery({ queryKey: keys.facts, queryFn: () => api.get<FactsPayload>("/api/facts") });
export const useGuardrails = () =>
  useQuery({ queryKey: keys.guardrails, queryFn: () => api.get<GuardrailsPayload>("/api/guardrails") });
export const useTrash = () => useQuery({ queryKey: keys.trash, queryFn: () => api.get<TrashItem[]>("/api/trash") });
export const useImportCandidates = () =>
  useQuery({ queryKey: keys.importCandidates, queryFn: () => api.get<ImportCandidate[]>("/api/import/candidates") });

/** Patch project metadata with an optimistic update of the cached detail + list. */
export function usePatchProject(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Partial<Project>) => api.patch<Project>(`/api/projects/${id}`, patch),
    onMutate: async (patch) => {
      await qc.cancelQueries({ queryKey: keys.project(id) });
      const prev = qc.getQueryData<ProjectDetail>(keys.project(id));
      if (prev) qc.setQueryData<ProjectDetail>(keys.project(id), { ...prev, project: { ...prev.project, ...patch } });
      return { prev };
    },
    onError: (_err, _patch, ctx) => {
      if (ctx?.prev) qc.setQueryData(keys.project(id), ctx.prev);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: keys.project(id) });
      qc.invalidateQueries({ queryKey: keys.projects });
    },
  });
}
