/**
 * Response shapes of the Resume Studio API. Request bodies that are Pydantic
 * models on the server are also generated into api-schema.d.ts
 * (`npm run gen:api`); the aliases at the bottom tie the two together so a
 * server-side model change surfaces here as a type error.
 */
import type { components } from "./api-schema";

type Schemas = components["schemas"];

export type TemplateKey = "classic" | "modern" | "compact";
export type ProjectStatus = "draft" | "applied" | "interviewing" | "offer" | "rejected" | "archived";
export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";
export type Severity = "error" | "warning" | "info";

export interface TemplateInfo {
  key: TemplateKey;
  label: string;
  description: string;
}

export interface ApiKeyStatus {
  set: boolean;
  source: "app" | "env" | null;
  last4: string | null;
}

export interface SystemInfo {
  version: string;
  claude: { found: boolean; path: string | null; version: string | null; logged_in: boolean | null; method: string | null };
  api_key: ApiKeyStatus;
  sample_loaded: boolean;
  word: boolean;
  platform: string;
  data_root: string;
  inputs: { profile: string | null; resume: string | null; fact_bank: number | null; deny_patterns: number };
  onboarding_needed: boolean;
  templates: TemplateInfo[];
  statuses: ProjectStatus[];
  models: string[];
  efforts: string[];
  active_jobs: JobSummary[];
}

export interface DenyHit {
  where: string;
  pattern: string;
  text: string;
}

export interface JobSummary {
  id: string;
  kind: "generate" | "render" | "fact_bank" | "ingest";
  label: string;
  project_id: string | null;
  status: JobStatus;
  stage: string;
  stages_seen: string[];
  error: string | null;
  hint: string | null;
  deny: DenyHit[];
  created: string;
  elapsed: number | null;
  line_count: number;
  result: Record<string, unknown> | null;
}

export interface LastRun {
  kind: string;
  when: string;
  ok: boolean;
  model: string | null;
  effort: string | null;
  error: string | null;
}

export interface Project {
  id: string;
  name: string;
  company: string;
  role: string;
  url: string;
  status: ProjectStatus;
  notes: string;
  applied_on: string | null;
  template: TemplateKey;
  cover_letter: boolean;
  created_at: string;
  updated_at: string;
  result_saved_at: string | null;
  rendered_at: string | null;
  last_generate: LastRun | null;
  last_render: LastRun | null;
  imported_from: string | null;
  has_result: boolean;
  has_pdf: boolean;
  inputs_changed: string[];
  outputs_stale: boolean;
  active_job: JobSummary | null;
}

export interface Contact {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  location: string;
  linkedin: string;
}

export interface Bullet {
  text: string;
  ids: string[];
}

export interface ExperienceEntry {
  company: string;
  location: string;
  dates: string;
  title: string;
  bullets: Bullet[];
}

export interface EducationEntry {
  institution: string;
  location: string;
  dates: string;
  degree: string;
}

export interface ResumeResult {
  schema: number;
  generated_at?: string;
  model?: string;
  effort?: string;
  template?: TemplateKey;
  inputs?: Record<string, string>;
  contact: Contact;
  summary: string;
  education: EducationEntry[];
  experience: ExperienceEntry[];
  skills: string[];
  cover_letter: Bullet[] | null;
  coverage?: { covered: string[]; missing: string[] };
  page_count?: number | null;
  draft?: string;
  warnings?: string[];
  generation_warnings?: string[];
}

export interface FileInfo {
  name: string;
  size: number;
  modified: string;
}

export interface ProjectDetail {
  project: Project;
  job_text: string;
  result: ResumeResult | null;
  outputs: FileInfo[];
  job: JobSummary | null;
}

export interface Version {
  id: string;
  files: FileInfo[];
  template: TemplateKey | null;
  generated_at: string | null;
  page_count: number | null;
  summary: string;
  warnings: number;
}

export interface LintIssue {
  kind: string;
  severity: Severity;
  message: string;
  value?: string;
}

export interface LintResult {
  summary: LintIssue[];
  bullets: Record<string, LintIssue[]>;
  skills: Record<string, LintIssue[]>;
  cover_letter: Record<string, LintIssue[]>;
  counts: Record<Severity, number>;
}

export interface FactInfo {
  text: string;
  employer: string;
  kind: string;
}

// Server-side Pydantic models (generated types). Fields filled by a
// default_factory are optional in the schema but always present in responses.
export type ProfileSection = Schemas["Section"] & { id: string };
export type Profile = Omit<Schemas["Profile"], "sections"> & { sections: ProfileSection[] };
export type ResumeStructure = Schemas["ResumeStructure"];
export type Fact = Schemas["Fact"];
export type Settings = Schemas["Settings"] & { model: string; effort: string };

export interface ProfilePayload {
  exists: boolean;
  file: string | null;
  updated: string | null;
  profile: Profile;
  backup?: string | null;
}

export interface ResumePayload {
  exists: boolean;
  file: string | null;
  updated: string | null;
  structure: ResumeStructure | null;
  originals: string[];
}

export interface UploadResult {
  upload_id: string;
  structure: ResumeStructure;
  needs_ai: boolean;
  prefill: {
    name: string;
    email: string;
    phone: string;
    location: string;
    linkedin: string;
    skills: string[];
  };
}

export interface FactsPayload {
  exists: boolean;
  facts: Fact[];
  companies: string[];
  kinds: string[];
  employer_issues: { id: string; employer: string }[];
}

export interface GuardrailsPayload {
  text: string;
  patterns: { line: number; pattern: string; error: string | null }[];
}

export interface TrashItem {
  id: string;
  name: string;
  company: string;
  deleted: string;
}

export interface ImportCandidate {
  file: string;
  company: string;
  role: string;
}
