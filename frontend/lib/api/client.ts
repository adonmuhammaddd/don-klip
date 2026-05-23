import type { DetectionConfig, JobListResponse, JobRead } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

export async function listJobs(page = 1, pageSize = 20): Promise<JobListResponse> {
  const res = await fetch(`${API_URL}/api/jobs?page=${page}&page_size=${pageSize}`, {
    cache: "no-store",
  });
  return handle<JobListResponse>(res);
}

export async function getJob(id: string): Promise<JobRead> {
  const res = await fetch(`${API_URL}/api/jobs/${id}`, { cache: "no-store" });
  return handle<JobRead>(res);
}

export async function createUrlJob(sourceUrl: string, config: DetectionConfig): Promise<JobRead> {
  const res = await fetch(`${API_URL}/api/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_url: sourceUrl, detection_config: config }),
  });
  return handle<JobRead>(res);
}

export async function createUploadJob(file: File, config: DetectionConfig): Promise<JobRead> {
  const form = new FormData();
  form.append("file", file);
  form.append("detection_config", JSON.stringify(config));
  const res = await fetch(`${API_URL}/api/jobs`, { method: "POST", body: form });
  return handle<JobRead>(res);
}

export async function deleteJob(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/jobs/${id}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(`API ${res.status}`);
  }
}
