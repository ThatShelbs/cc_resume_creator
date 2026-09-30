/**
 * Thin fetch wrapper for the Resume Studio API. Every call carries the
 * per-launch session token the server injected into index.html; links that
 * can't set headers (downloads, the PDF viewer, EventSource) pass it as ?t=.
 */

const injected = document.querySelector('meta[name="studio-token"]')?.getAttribute("content");
export const TOKEN: string =
  injected && injected !== "__STUDIO_TOKEN__" ? injected : (import.meta.env.VITE_STUDIO_TOKEN ?? "dev");

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function messageFrom(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      // FastAPI validation errors: [{loc, msg}]
      return detail
        .map((d: { msg?: string; loc?: unknown[] }) => {
          const field = Array.isArray(d.loc) ? d.loc.filter((x) => x !== "body").join(".") : "";
          return field ? `${field}: ${(d.msg ?? "").replace(/^Value error, /, "")}` : (d.msg ?? "");
        })
        .join("; ");
    }
  }
  return fallback;
}

async function request<T>(method: string, path: string, body?: unknown, init?: RequestInit): Promise<T> {
  const isForm = body instanceof FormData;
  let res: Response;
  try {
    res = await fetch(path, {
      method,
      headers: {
        "X-Studio-Token": TOKEN,
        ...(body !== undefined && !isForm ? { "Content-Type": "application/json" } : {}),
      },
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
      ...init,
    });
  } catch {
    throw new ApiError("Can't reach Resume Studio. Is the launcher window still open?", 0);
  }
  const text = await res.text();
  let data: unknown = text;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    /* plain-text endpoints */
  }
  if (!res.ok) throw new ApiError(messageFrom(data, `Request failed (${res.status})`), res.status);
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, body),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
  del: <T>(path: string) => request<T>("DELETE", path),
  upload: <T>(path: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<T>("POST", path, form);
  },
};

export function withToken(url: string): string {
  return `${url}${url.includes("?") ? "&" : "?"}t=${encodeURIComponent(TOKEN)}`;
}

export function projectFileUrl(pid: string, name: string, opts: { download?: boolean; bust?: string } = {}) {
  let url = `/api/projects/${encodeURIComponent(pid)}/files/${encodeURIComponent(name)}`;
  const params = [opts.download ? "download=true" : "", opts.bust ? `v=${encodeURIComponent(opts.bust)}` : ""].filter(Boolean);
  if (params.length) url += `?${params.join("&")}`;
  return withToken(url);
}

export function versionFileUrl(pid: string, vid: string, name: string) {
  return withToken(
    `/api/projects/${encodeURIComponent(pid)}/versions/${encodeURIComponent(vid)}/files/${encodeURIComponent(name)}`,
  );
}
