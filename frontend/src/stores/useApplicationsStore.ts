import { create } from 'zustand';
import { Applications } from '../api/endpoints';

export interface Application {
  id: number;
  job: number;
  job_detail?: {
    id: number;
    title: string;
    company?: { name: string };
    location?: string;
    remote?: boolean;
    salary_min?: number | null;
    salary_max?: number | null;
    apply_url?: string;
    ghost_band?: string;
  };
  status: string;
  tier_used: string;
  notes?: string;
  next_action?: string;
  follow_up_on?: string | null;
  created_at?: string;
  updated_at?: string;
  events?: { id: number; type: string; payload?: { status?: string } | null; created_at?: string }[];
}

interface AppState {
  applications: Application[];
  fetch: () => Promise<void>;
  create: (jobId: number, tier?: string, status?: string) => Promise<Application>;
  setStatus: (id: number, status: string) => Promise<void>;
  patchApp: (id: number, payload: Partial<Application>) => Promise<void>;
  remove: (id: number) => Promise<void>;
}

export const useApplicationsStore = create<AppState>((set, get) => ({
  applications: [],
  fetch: async () => {
    const data = await Applications.list();
    set({ applications: data.results ?? data });
  },
  create: async (jobId, tier, status) => {
    const app = await Applications.create(jobId, tier, status);
    set({ applications: [app, ...get().applications] });
    return app;
  },
  setStatus: async (id, status) => {
    await Applications.patch(id, { status });
    set({
      applications: get().applications.map((a) =>
        a.id === id ? { ...a, status } : a,
      ),
    });
  },
  patchApp: async (id, payload) => {
    const updated = await Applications.patch(id, payload);
    set({
      applications: get().applications.map((a) =>
        a.id === id ? { ...a, ...updated } : a,
      ),
    });
  },
  remove: async (id) => {
    await Applications.remove(id);
    set({ applications: get().applications.filter((a) => a.id !== id) });
  },
}));
