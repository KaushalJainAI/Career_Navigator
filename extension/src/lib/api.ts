/** Background-worker API client. Reads token + backend URL from chrome.storage. */

import type { ParsedPosting, ParsedProfile } from './types';

interface Settings {
  backend: string;
  token: string;
}

export async function getSettings(): Promise<Settings> {
  const all = await chrome.storage.local.get(['backend', 'token']);
  return {
    backend: all.backend || 'http://localhost:8000',
    token: all.token || '',
  };
}

async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const { backend, token } = await getSettings();
  if (!token) {
    throw new Error('No API token configured. Paste one in the popup.');
  }
  const headers = new Headers(init.headers || {});
  headers.set('Authorization', `Token ${token}`);
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  return fetch(`${backend}/api/v1${path}`, { ...init, headers });
}

export async function postPageContext(posting: ParsedPosting) {
  const resp = await authFetch('/ext/page-context/', {
    method: 'POST',
    body: JSON.stringify(posting),
  });
  if (!resp.ok) throw new Error(`page-context failed: ${resp.status}`);
  return resp.json() as Promise<{ job_id: number | null; stealth_blocked: boolean }>;
}

export async function getAutofill(jobId: number) {
  const resp = await authFetch(`/ext/autofill/?job_id=${jobId}`);
  if (!resp.ok) throw new Error(`autofill failed: ${resp.status}`);
  return resp.json();
}

export async function postSubmitEvent(payload: Record<string, unknown>) {
  const resp = await authFetch('/ext/submit-event/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(`submit-event failed: ${resp.status}`);
  return resp.json();
}

export async function postProfileContext(profile: ParsedProfile) {
  const resp = await authFetch('/ext/profile-context/', {
    method: 'POST',
    body: JSON.stringify(profile),
  });
  if (!resp.ok) throw new Error(`profile-context failed: ${resp.status}`);
  return resp.json();
}

export async function ping() {
  const resp = await authFetch('/auth/me/');
  if (!resp.ok) throw new Error(`ping failed: ${resp.status}`);
  return resp.json() as Promise<{ id: number; email: string }>;
}
