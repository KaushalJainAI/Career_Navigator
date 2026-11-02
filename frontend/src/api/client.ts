import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';

const baseURL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api/v1';

export const api = axios.create({ baseURL, withCredentials: true });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cn_access');
  if (token && config.headers) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Access tokens expire; transparently refresh once and retry the request.
let refreshing: Promise<string | null> | null = null;

async function refreshAccess(): Promise<string | null> {
  const refresh = localStorage.getItem('cn_refresh');
  if (!refresh) return null;
  try {
    const r = await axios.post(`${baseURL}/auth/refresh/`, { refresh });
    localStorage.setItem('cn_access', r.data.access);
    if (r.data.refresh) localStorage.setItem('cn_refresh', r.data.refresh);
    return r.data.access as string;
  } catch {
    return null;
  }
}

api.interceptors.response.use(undefined, async (error: AxiosError) => {
  const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
  const isAuthCall = original?.url?.includes('/auth/login') || original?.url?.includes('/auth/refresh');
  if (error.response?.status === 401 && original && !original._retried && !isAuthCall) {
    original._retried = true;
    refreshing = refreshing ?? refreshAccess().finally(() => { refreshing = null; });
    const token = await refreshing;
    if (token) {
      original.headers.Authorization = `Bearer ${token}`;
      return api(original);
    }
  }
  return Promise.reject(error);
});

export function errorMessage(e: unknown, fallback = 'Something went wrong. Please try again.'): string {
  const err = e as AxiosError<{ detail?: string } & Record<string, unknown>>;
  const data = err?.response?.data;
  if (data && typeof data === 'object') {
    if (typeof data.detail === 'string') return data.detail;
    const first = Object.values(data)[0];
    if (Array.isArray(first) && typeof first[0] === 'string') return first[0];
  }
  if (err?.code === 'ERR_NETWORK') return 'Cannot reach the server. Is the backend running?';
  return fallback;
}

export const wsUrl = (path: string) => {
  const base = (import.meta.env.VITE_WS_URL as string) || 'ws://localhost:8000';
  return `${base}${path}`;
};
