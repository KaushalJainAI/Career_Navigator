import { create } from 'zustand';

export type Theme = 'light' | 'dark' | 'system';
const KEY = 'cn_theme';

function systemDark(): boolean {
  return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-color-scheme: dark)').matches;
}

export function resolveTheme(t: Theme): 'light' | 'dark' {
  return t === 'system' ? (systemDark() ? 'dark' : 'light') : t;
}

export function applyTheme(t: Theme): void {
  if (typeof document === 'undefined') return;
  document.documentElement.classList.toggle('dark', resolveTheme(t) === 'dark');
}

function stored(): Theme {
  if (typeof localStorage === 'undefined') return 'system';
  return (localStorage.getItem(KEY) as Theme) || 'system';
}

/** Apply the persisted theme on boot (call before render to avoid a flash),
 *  and keep 'system' in sync with OS changes. */
export function initTheme(): void {
  applyTheme(stored());
  window.matchMedia?.('(prefers-color-scheme: dark)').addEventListener?.('change', () => {
    if (stored() === 'system') applyTheme('system');
  });
}

interface ThemeState {
  theme: Theme;
  setTheme: (t: Theme) => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
  theme: stored(),
  setTheme: (t) => {
    if (typeof localStorage !== 'undefined') localStorage.setItem(KEY, t);
    applyTheme(t);
    set({ theme: t });
  },
}));
