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
  passwordReset: (email: string) =>
    api.post('/auth/password-reset/', { email }).then((r) => r.data),
  passwordResetConfirm: (uid: string, token: string, password: string) =>
    api.post('/auth/password-reset/confirm/', { uid, token, password }).then((r) => r.data),
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

export const Account = {
  update: (payload: { first_name?: string; last_name?: string; stealth_domains?: string[] }) =>
    api.patch('/auth/me/', payload).then((r) => r.data),
  changePassword: (current_password: string, new_password: string) =>
    api.post('/auth/change-password/', { current_password, new_password }).then((r) => r.data),
};

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
  importText: (text: string, label = 'Pasted resume') =>
    api.post('/resumes/import-text/', { text, label }).then((r) => r.data),
  makeMaster: (id: number, overwrite_profile = false) =>
    api.post(`/resumes/${id}/make-master/`, { overwrite_profile }).then((r) => r.data),
  remove: (id: number) => api.delete(`/resumes/${id}/`).then((r) => r.data),
};

export const Jobs = {
  list: (params: Record<string, string | number | boolean> = {}) =>
    api.get('/jobs/', { params }).then((r) => r.data),
  detail: (id: number) => api.get(`/jobs/${id}/`).then((r) => r.data),
  match: (id: number) => api.get(`/matching/jobs/${id}/`).then((r) => r.data),
  feed: (params: Record<string, string | number | boolean> = {}) =>
    api.get('/matching/feed/', { params }).then((r) => r.data),
  refresh: () => api.post('/jobs/refresh/', {}, { timeout: 180000 }).then((r) => r.data),
  add: (payload: Record<string, unknown>) => api.post('/jobs/add/', payload).then((r) => r.data),
};

export const Applications = {
  list: () => api.get('/applications/').then((r) => r.data),
  stats: () => api.get('/applications/stats/').then((r) => r.data),
  analytics: () => api.get('/applications/analytics/').then((r) => r.data),
  prepare: (jobId: number, tier: 'assist' | 'autofill' | 'autonomous') =>
    api.post('/applications/prepare/', { job_id: jobId, tier }).then((r) => r.data),
  create: (jobId: number, tier?: string) =>
    api.post('/applications/', { job: jobId, tier_used: tier }).then((r) => r.data),
  patch: (id: number, payload: Record<string, unknown>) =>
    api.patch(`/applications/${id}/`, payload).then((r) => r.data),
  approve: (id: number) =>
    api.post(`/applications/${id}/approve/`).then((r) => r.data as { approval_token: string }),
  today: () => api.get('/applications/today/').then((r) => r.data),
  followedUp: (id: number) => api.post(`/applications/${id}/followed-up/`).then((r) => r.data),
};

export const Tailoring = {
  resume: (applicationId: number) =>
    api.post('/tailoring/resume/', { application_id: applicationId }).then((r) => r.data),
  getResume: (applicationId: number) =>
    api.get('/tailoring/resume/', { params: { application_id: applicationId } }).then((r) => r.data),
  editResume: (id: number, content: Record<string, unknown>) =>
    api.patch(`/tailoring/resume/${id}/`, { content }).then((r) => r.data),
  coverLetter: (applicationId: number) =>
    api.post('/tailoring/cover-letter/', { application_id: applicationId }).then((r) => r.data),
  getCoverLetter: (applicationId: number) =>
    api.get('/tailoring/cover-letter/', { params: { application_id: applicationId } }).then((r) => r.data),
  editCoverLetter: (id: number, content: string) =>
    api.patch(`/tailoring/cover-letter/${id}/`, { content }).then((r) => r.data),
  exportResume: (applicationId: number, fmt: 'txt' | 'docx' = 'txt') =>
    api.get('/tailoring/resume/export/', {
      params: { application_id: applicationId, fmt },
      responseType: 'blob',
    }).then((r) => r.data as Blob),
};

export const Interview = {
  start: (payload: { role?: string; stage: string; difficulty?: string; company?: number; application?: number }) =>
    api.post('/interview/sessions/', payload).then((r) => r.data),
  detail: (id: number) => api.get(`/interview/sessions/${id}/`).then((r) => r.data),
  answer: (id: number, answer: string) =>
    api.post(`/interview/sessions/${id}/answer/`, { answer }).then((r) => r.data),
  report: (id: number) => api.post(`/interview/sessions/${id}/report/`).then((r) => r.data),
  list: () => api.get('/interview/sessions/').then((r) => r.data),
};

export const Agent = {
  sessions: () => api.get('/agent/sessions/').then((r) => r.data),
  start: (kind: string) => api.post('/agent/sessions/', { kind }).then((r) => r.data),
  chat: (sessionId: number, message: string, phase_cap = 1) =>
    api.post(`/agent/sessions/${sessionId}/chat/`, { message, phase_cap }).then((r) => r.data),
};

export const ApiTokens = {
  list: () => api.get('/auth/api-tokens/').then((r) => r.data),
  create: (name: string) =>
    api.post('/auth/api-tokens/', { name }).then((r) => r.data as {
      id: number; name: string; token: string; created_at: string;
    }),
  revoke: (id: number) =>
    api.post(`/auth/api-tokens/${id}/revoke/`).then((r) => r.data),
};

export const Network = {
  graph: (root = 'user:self', depth = 1) =>
    api.get('/networking/graph/', { params: { root, depth } }).then((r) => r.data as {
      nodes: { id: string; type: string; data: Record<string, unknown> }[];
      edges: { id: string; source: string; target: string; label: string }[];
    }),
  warmIntros: (companyId: number, maxHops = 2) =>
    api.get(`/networking/warm-intros/${companyId}/`, { params: { max_hops: maxHops } })
       .then((r) => r.data),
  contacts: {
    list: (params: Record<string, string | number> = {}) =>
      api.get('/networking/contacts/', { params }).then((r) => r.data),
    create: (payload: Record<string, unknown>) =>
      api.post('/networking/contacts/', payload).then((r) => r.data),
    patch: (id: number, payload: Record<string, unknown>) =>
      api.patch(`/networking/contacts/${id}/`, payload).then((r) => r.data),
    remove: (id: number) =>
      api.delete(`/networking/contacts/${id}/`).then((r) => r.data),
  },
  employments: {
    list: (contactId: number) =>
      api.get(`/networking/contacts/${contactId}/employments/`).then((r) => r.data),
    create: (contactId: number, payload: Record<string, unknown>) =>
      api.post(`/networking/contacts/${contactId}/employments/`, payload).then((r) => r.data),
    remove: (id: number) =>
      api.delete(`/networking/employments/${id}/`).then((r) => r.data),
  },
  relationships: {
    list: (contactId: number) =>
      api.get(`/networking/contacts/${contactId}/relationships/`).then((r) => r.data),
    create: (contactId: number, payload: Record<string, unknown>) =>
      api.post(`/networking/contacts/${contactId}/relationships/`, payload).then((r) => r.data),
    remove: (id: number) =>
      api.delete(`/networking/relationships/${id}/`).then((r) => r.data),
  },
};

export const Notifications = {
  subscriptions: () => api.get('/notifications/subscriptions/').then((r) => r.data),
  createSubscription: (payload: Record<string, unknown>) =>
    api.post('/notifications/subscriptions/', payload).then((r) => r.data),
  patchSubscription: (id: number, payload: Record<string, unknown>) =>
    api.patch(`/notifications/subscriptions/${id}/`, payload).then((r) => r.data),
  deleteSubscription: (id: number) =>
    api.delete(`/notifications/subscriptions/${id}/`).then((r) => r.data),
  alerts: () => api.get('/notifications/alerts/').then((r) => r.data),
  markRead: (id: number) => api.post(`/notifications/alerts/${id}/read/`).then((r) => r.data),
};

export const Billing = {
  summary: () => api.get('/billing/summary/').then((r) => r.data),
  ledger: () => api.get('/billing/ledger/').then((r) => r.data),
  topUp: (amount: number) => api.post('/billing/top-up/', { amount }).then((r) => r.data),
};

export const Copilot = {
  latest: () => api.get('/agent/copilot/latest/').then((r) => r.data),
  session: (id: number) => api.get(`/agent/copilot/${id}/`).then((r) => r.data),
  send: (message: string, session_id?: number | null) =>
    api.post('/agent/copilot/', { message, session_id }, { timeout: 180000 }).then((r) => r.data),
  approve: (session_id: number, action_id: string, approve: boolean) =>
    api.post(`/agent/copilot/${session_id}/approve/`, { action_id, approve }, { timeout: 180000 }).then((r) => r.data),
};

export const AI = {
  status: () => api.get('/ai/status/').then((r) => r.data),
};
