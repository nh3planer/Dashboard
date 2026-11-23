import type { Project, Summary } from './types';

const BASE = import.meta.env.DEV ? '' : '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { error?: string }).error ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function fetchSummary(): Promise<Summary> {
  return request<Summary>('/summary');
}

export function fetchProjects(details = false): Promise<Project[]> {
  return request<Project[]>(`/projects${details ? '?details=true' : ''}`);
}

export function fetchProject(id: number): Promise<Project> {
  return request<Project>(`/projects/${id}`);
}

export function updateProject(id: number, data: Partial<Project>): Promise<{ ok: boolean }> {
  return request(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) });
}

export function updateMilestone(id: number, data: Record<string, unknown>): Promise<{ ok: boolean }> {
  return request(`/milestones/${id}`, { method: 'PUT', body: JSON.stringify(data) });
}
