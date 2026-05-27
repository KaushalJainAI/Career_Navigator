import { create } from 'zustand';
import type { AxiosError } from 'axios';
import { Auth } from '../api/endpoints';

interface User {
  id: number;
  email: string;
  cn_profile?: { tier: string; credits_remaining: number };
}

interface AuthState {
  user: User | null;
  loading: boolean;
  initialized: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (code: string, redirectUri?: string) => Promise<void>;
  requestPasswordReset: (email: string) => Promise<string>;
  confirmPasswordReset: (uid: string, token: string, password: string) => Promise<string>;
  logout: () => void;
  refresh: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,
  initialized: false,
  error: null,
  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const tokens = await Auth.login(email, password);
      localStorage.setItem('cn_access', tokens.access);
      localStorage.setItem('cn_refresh', tokens.refresh);
      const me = await Auth.me();
      set({ user: me, loading: false });
    } catch (e) {
      const message = getErrorMessage(e);
      set({ error: message, loading: false });
      throw new Error(message);
    }
  },
  register: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const out = await Auth.register(email, password);
      localStorage.setItem('cn_access', out.access);
      localStorage.setItem('cn_refresh', out.refresh);
      set({ user: out.user, loading: false });
    } catch (e) {
      const message = getErrorMessage(e);
      set({ error: message, loading: false });
      throw new Error(message);
    }
  },
  loginWithGoogle: async (code, redirectUri) => {
    set({ loading: true, error: null });
    try {
      const out = await Auth.google(code, redirectUri);
      localStorage.setItem('cn_access', out.access);
      localStorage.setItem('cn_refresh', out.refresh);
      set({ user: out.user, loading: false });
    } catch (e) {
      const message = getErrorMessage(e);
      set({ error: message, loading: false });
      throw new Error(message);
    }
  },
  requestPasswordReset: async (email) => {
    set({ loading: true, error: null });
    try {
      const out = await Auth.passwordReset(email);
      set({ loading: false });
      return out.detail;
    } catch (e) {
      set({ error: getErrorMessage(e), loading: false });
      throw e;
    }
  },
  confirmPasswordReset: async (uid, token, password) => {
    set({ loading: true, error: null });
    try {
      const out = await Auth.passwordResetConfirm(uid, token, password);
      set({ loading: false });
      return out.detail;
    } catch (e) {
      set({ error: getErrorMessage(e), loading: false });
      throw e;
    }
  },
  logout: () => {
    localStorage.removeItem('cn_access');
    localStorage.removeItem('cn_refresh');
    set({ user: null });
  },
  refresh: async () => {
    const token = localStorage.getItem('cn_access');
    if (!token) {
      set({ user: null, initialized: true });
      return;
    }
    set({ loading: true });
    try {
      const me = await Auth.me();
      set({ user: me, loading: false, initialized: true });
    } catch {
      localStorage.removeItem('cn_access');
      localStorage.removeItem('cn_refresh');
      set({ user: null, loading: false, initialized: true });
    }
  },
}));

function getErrorMessage(error: unknown): string {
  const axiosError = error as AxiosError<Record<string, unknown>>;
  const data = axiosError.response?.data;
  if (data) {
    const detail = data.detail;
    if (typeof detail === 'string') return detail;
    const firstField = Object.values(data).find((value) => Array.isArray(value) || typeof value === 'string');
    if (typeof firstField === 'string') return firstField;
    if (Array.isArray(firstField) && typeof firstField[0] === 'string') return firstField[0];
  }
  return error instanceof Error ? error.message : 'Something went wrong.';
}
