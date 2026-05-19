import { create } from 'zustand';
import { Auth } from '../api/endpoints';

interface User {
  id: number;
  email: string;
  cn_profile?: { tier: string; credits_remaining: number };
}

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (code: string, redirectUri?: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,
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
      set({ error: (e as Error).message, loading: false });
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
      set({ error: (e as Error).message, loading: false });
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
      set({ error: (e as Error).message, loading: false });
    }
  },
  logout: () => {
    localStorage.removeItem('cn_access');
    localStorage.removeItem('cn_refresh');
    set({ user: null });
  },
  refresh: async () => {
    try {
      const me = await Auth.me();
      set({ user: me });
    } catch {
      set({ user: null });
    }
  },
}));
