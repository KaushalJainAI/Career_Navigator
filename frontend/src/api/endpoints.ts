import { api } from './client';

export const Auth = {
  register: (email: string, password: string) =>
    api.post('/auth/register/', { email, password }).then((r) => r.data),
  login: (email: string, password: string) =>
    api.post('/auth/login/', { username: email, password }).then((r) => r.data),
  me: () => api.get('/auth/me/').then((r) => r.data),
  guestKey: () => api.post('/auth/guest-key/').then((r) => r.data),
  google: (code: string, redirect_uri?: string) =>
    api.post('/auth/google/', { code, redirect_uri }).then((r) => r.data),
};

/** Builds the front-channel Google OAuth URL. Google redirects back to
 *  redirect_uri with ?code=…; we POST that to /auth/google/ for JWTs. */
export function buildGoogleAuthUrl(): string {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string;
  const redirectUri =
    (import.meta.env.VITE_GOOGLE_REDIRECT_URI as string)
    || `${window.location.origin}/auth/google/callback`;
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: 'code',
    scope: 'openid email profile',
    access_type: 'offline',
    prompt: 'consent',
    include_granted_scopes: 'true',
  });
  return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
}

export const Profile = {
  get: () => api.get('/profile/').then((r) => r.data),
  patch: (payload: Record<string, unknown>) => api.patch('/profile/', payload).then((r) => r.data),
};

export const Resumes = {
  list: () => api.get('/resumes/').then((r) => r.data),
  upload: (file: File, label = 'Master Resume') => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('label', label);
    return api.post('/resumes/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      .then((r) => r.data);
  },
};

export const Jobs = {
  list: (params: Record<string, string | number | boolean> = {}) =>
    api.get('/jobs/', { params }).then((r) => r.data),
  detail: (id: number) => api.get(`/jobs/${id}/`).then((r) => r.data),
  match: (id: number) => api.get(`/matching/jobs/${id}/`).then((r) => r.data),
};

export const Applications = {
  list: () => api.get('/applications/').then((r) => r.data),
  create: (jobId: number, tier?: string) =>
    api.post('/applications/', { job: jobId, tier_used: tier }).then((r) => r.data),
  patch: (id: number, payload: Record<string, unknown>) =>
    api.patch(`/applications/${id}/`, payload).then((r) => r.data),
  approve: (id: number) =>
    api.post(`/applications/${id}/approve/`).then((r) => r.data as { approval_token: string }),
};

export const Tailoring = {
  resume: (applicationId: number) =>
    api.post('/tailoring/resume/', { application_id: applicationId }).then((r) => r.data),
  coverLetter: (applicationId: number) =>
    api.post('/tailoring/cover-letter/', { application_id: applicationId }).then((r) => r.data),
};

export const Interview = {
  start: (payload: { role: string; stage: string; difficulty?: string; company?: number }) =>
    api.post('/interview/sessions/', payload).then((r) => r.data),
  detail: (id: number) => api.get(`/interview/sessions/${id}/`).then((r) => r.data),
  answer: (id: number, answer: string) =>
    api.post(`/interview/sessions/${id}/answer/`, { answer }).then((r) => r.data),
  report: (id: number) => api.post(`/interview/sessions/${id}/report/`).then((r) => r.data),
};

export const Agent = {
  sessions: () => api.get('/agent/sessions/').then((r) => r.data),
  start: (kind: string) => api.post('/agent/sessions/', { kind }).then((r) => r.data),
  chat: (sessionId: number, message: string, phase_cap = 1) =>
    api.post(`/agent/sessions/${sessionId}/chat/`, { message, phase_cap }).then((r) => r.data),
};

export const Notifications = {
  subscriptions: () => api.get('/notifications/subscriptions/').then((r) => r.data),
  createSubscription: (payload: Record<string, unknown>) =>
    api.post('/notifications/subscriptions/', payload).then((r) => r.data),
  alerts: () => api.get('/notifications/alerts/').then((r) => r.data),
};
